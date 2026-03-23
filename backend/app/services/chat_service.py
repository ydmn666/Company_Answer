import json
import logging
import re
from collections.abc import Iterator
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.logging_utils import log_event
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.user import User
from app.schemas.chat import (
    AskResponse,
    CitationItem,
    ChatMessageItem,
    ChatSessionDetail,
    ChatSessionItem,
    SessionActionResponse,
    UpdateSessionRequest,
)
from app.services.cache_service import get_cached_answer, knowledge_base_fingerprint, set_cached_answer
from app.services.llm_service import answer_with_rag, stream_chat_completion
from app.services.retrieval_service import retrieve_top_chunks, tokenize


logger = logging.getLogger(__name__)

CONTEXT_MESSAGE_LIMIT = 6
REFERENTIAL_PATTERN = re.compile(r"^(那|那么|这个|这个制度|该|其|它|上述|上面|这里|继续|然后|那它|那这个)")
SHORT_FOLLOWUP_PATTERN = re.compile(r"(呢|吗|么|如何|多久|多少|哪些|怎么|为什么|是否)")


def _trace(event: str, **payload) -> None:
    log_event(logger, event, **payload)


def _ensure_session(db: Session, user: User, session_id: str | None, question: str) -> ChatSession:
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
            .first()
        )
        if session:
            return session

    session = ChatSession(
        user_id=user.id,
        title=(question[:60] or "新会话"),
        updated_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()
    return session


def _commit_session_visibility(db: Session, session: ChatSession) -> ChatSession:
    db.commit()
    db.refresh(session)
    return session


def _sorted_messages(session: ChatSession) -> list[ChatMessage]:
    return sorted(session.messages, key=lambda item: item.created_at)


def _build_recent_history(session: ChatSession, limit: int = CONTEXT_MESSAGE_LIMIT) -> list[dict]:
    messages = _sorted_messages(session)
    return [{"role": item.role, "content": item.content} for item in messages[-limit:]]


def _extract_recent_subject(history_messages: list[dict]) -> str:
    for item in reversed(history_messages):
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if item.get("role") == "user":
            return content
    for item in reversed(history_messages):
        content = (item.get("content") or "").strip()
        if content:
            return content
    return ""


def _looks_like_followup(question: str, history_messages: list[dict]) -> bool:
    trimmed = (question or "").strip()
    if not trimmed or not history_messages:
        return False
    if REFERENTIAL_PATTERN.match(trimmed):
        return True
    if len(trimmed) <= 12 and SHORT_FOLLOWUP_PATTERN.search(trimmed):
        return True
    if len(tokenize(trimmed)) <= 4 and SHORT_FOLLOWUP_PATTERN.search(trimmed):
        return True
    return False


def _rewrite_question(question: str, history_messages: list[dict]) -> str:
    trimmed = (question or "").strip()
    if not trimmed:
        return trimmed
    if not _looks_like_followup(trimmed, history_messages):
        return trimmed

    anchor = _extract_recent_subject(history_messages)
    if not anchor:
        return trimmed
    return f"基于前文“{anchor[:80]}”，回答这个追问：{trimmed}"


def _build_generation_messages(history_messages: list[dict], rewritten_question: str) -> list[dict]:
    recent_history = history_messages[-CONTEXT_MESSAGE_LIMIT:]
    return [*recent_history, {"role": "user", "content": rewritten_question}]


def _build_citations(chunks: list[dict]) -> list[dict]:
    return [
        {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "document_title": item["document_title"],
            "snippet": item["snippet"],
            "page_no": item.get("page_no"),
            "section_title": item.get("section_title"),
            "chunk_index": item.get("chunk_index"),
        }
        for item in chunks[:3]
    ]


def _prepare_rag(
    db: Session,
    session: ChatSession,
    question: str,
    provider: str | None,
) -> tuple[str, str, dict | None, list[dict], list[dict]]:
    started = datetime.utcnow()
    history_messages = _build_recent_history(session)
    rewritten_question = _rewrite_question(question, history_messages)
    fingerprint = knowledge_base_fingerprint(db)
    cached = get_cached_answer(rewritten_question, provider, fingerprint)
    retrieval_context = [] if cached else retrieve_top_chunks(db, rewritten_question)
    elapsed_ms = round((datetime.utcnow() - started).total_seconds() * 1000, 2)
    _trace(
        "prepare_rag.done",
        session_id=session.id,
        cached=bool(cached),
        retrieval_count=len(retrieval_context),
        elapsed_ms=elapsed_ms,
    )
    return rewritten_question, fingerprint, cached, retrieval_context, history_messages


def _persist_answer(
    db: Session,
    session: ChatSession,
    question: str,
    answer: str,
    citations: list[dict],
) -> None:
    db.add(ChatMessage(session_id=session.id, role="user", content=question))
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
            citations_json=json.dumps(citations, ensure_ascii=False),
        )
    )
    session.updated_at = datetime.utcnow()
    db.commit()


def ask_question(
    db: Session,
    user: User,
    question: str,
    session_id: str | None = None,
    provider: str | None = None,
) -> AskResponse:
    session = _ensure_session(db, user, session_id, question)
    session = _commit_session_visibility(db, session)
    rewritten_question, fingerprint, cached, retrieval_context, history_messages = _prepare_rag(
        db, session, question, provider
    )

    if cached:
        rag_result = cached
    else:
        messages = _build_generation_messages(history_messages, rewritten_question)
        rag_result = answer_with_rag(messages, retrieval_context, provider)
        rag_result["rewritten_question"] = rewritten_question
        set_cached_answer(rewritten_question, provider, fingerprint, rag_result)

    _persist_answer(db, session, question, rag_result["answer"], rag_result["citations"])

    return AskResponse(
        session_id=session.id,
        answer=rag_result["answer"],
        citations=rag_result["citations"],
        provider_used=rag_result["provider_used"],
        rewritten_question=rewritten_question,
    )


def stream_question(
    db: Session,
    user: User,
    question: str,
    session_id: str | None = None,
    provider: str | None = None,
) -> Iterator[str]:
    session = _ensure_session(db, user, session_id, question)
    session = _commit_session_visibility(db, session)
    _trace("stream_question.start", session_id=session.id, provider=provider or "local")
    rewritten_question, fingerprint, cached, retrieval_context, history_messages = _prepare_rag(
        db, session, question, provider
    )
    citations = _build_citations(retrieval_context)

    def encode(event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    yield encode("session", {"session_id": session.id, "rewritten_question": rewritten_question})

    if cached:
        _trace("stream_question.cached", session_id=session.id)
        answer = cached["answer"]
        provider_used = cached.get("provider_used", provider or "local")
        citations = cached.get("citations", citations)
        yield encode("citations", {"citations": citations})
        if answer:
            yield encode("token", {"content": answer})
        _persist_answer(db, session, question, answer, citations)
        yield encode(
            "done",
            {
                "provider_used": provider_used,
                "answer": answer,
                "citations": citations,
                "rewritten_question": rewritten_question,
            },
        )
        return

    yield encode("citations", {"citations": citations})
    _trace("stream_question.citations_sent", session_id=session.id, citation_count=len(citations))

    answer_parts: list[str] = []
    messages = _build_generation_messages(history_messages, rewritten_question)
    stream, provider_used = stream_chat_completion(messages, retrieval_context, provider)
    try:
        for chunk in stream:
            if not chunk:
                continue
            answer_parts.append(chunk)
            _trace("stream_question.token", session_id=session.id, chunk_size=len(chunk))
            yield encode("token", {"content": chunk})

        answer = "".join(answer_parts).strip()
        if not answer:
            _trace("stream_question.empty_answer", session_id=session.id, provider=provider_used)
            logger.warning(
                "stream_question empty answer session_id=%s provider=%s rewritten_question=%s",
                session.id,
                provider_used,
                rewritten_question,
            )
            fallback_answer = "当前回答未正常生成，已结束本次请求，请稍后重试。"
            _persist_answer(db, session, question, fallback_answer, citations)
            yield encode(
                "done",
                {
                    "provider_used": "local",
                    "answer": fallback_answer,
                    "citations": citations,
                    "rewritten_question": rewritten_question,
                },
            )
            return

        _trace("stream_question.done", session_id=session.id, provider=provider_used, answer_size=len(answer))
        rag_result = {
            "answer": answer,
            "citations": citations,
            "provider_used": provider_used,
            "rewritten_question": rewritten_question,
        }
        set_cached_answer(rewritten_question, provider, fingerprint, rag_result)
        _persist_answer(db, session, question, answer, citations)
        yield encode(
            "done",
            {
                "provider_used": provider_used,
                "answer": answer,
                "citations": citations,
                "rewritten_question": rewritten_question,
            },
        )
    except Exception as exc:
        db.rollback()
        _trace("stream_question.exception", session_id=session.id, provider=provider or "local", error=repr(exc))
        logger.exception(
            "stream_question exception session_id=%s provider=%s rewritten_question=%s",
            session.id,
            provider,
            rewritten_question,
        )
        fallback_answer = "当前回答流式生成异常，已结束本次请求，请稍后重试。"
        yield encode("error", {"detail": str(exc)})
        yield encode(
            "done",
            {
                "provider_used": "local",
                "answer": fallback_answer,
                "citations": citations,
                "rewritten_question": rewritten_question,
            },
        )


def list_sessions(db: Session, user: User) -> list[ChatSessionItem]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.pinned.desc(), ChatSession.pinned_at.desc(), ChatSession.updated_at.desc())
        .all()
    )
    return [
        ChatSessionItem(
            id=item.id,
            title=item.title,
            pinned=item.pinned,
            pinned_at=item.pinned_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
            message_count=len(item.messages),
        )
        for item in sessions
    ]


def get_session(db: Session, user: User, session_id: str) -> ChatSessionDetail | None:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        return None

    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        pinned=session.pinned,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            ChatMessageItem(
                id=message.id,
                role=message.role,
                content=message.content,
                citations=[CitationItem.model_validate(item) for item in json.loads(message.citations_json or "[]")],
                created_at=message.created_at,
            )
            for message in _sorted_messages(session)
        ],
    )


def update_session(
    db: Session,
    user: User,
    session_id: str,
    payload: UpdateSessionRequest,
) -> ChatSessionDetail | None:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        return None

    if payload.title is not None:
        title = payload.title.strip()
        if title:
            session.title = title[:255]

    if payload.pinned is not None:
        session.pinned = payload.pinned
        session.pinned_at = datetime.utcnow() if payload.pinned else None

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return get_session(db, user, session_id)


def delete_session(db: Session, user: User, session_id: str) -> SessionActionResponse | None:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        return None

    db.delete(session)
    db.commit()
    return SessionActionResponse(id=session_id, message="Session deleted")
