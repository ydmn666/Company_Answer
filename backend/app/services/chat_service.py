import json
from collections.abc import Iterator
from datetime import datetime

from sqlalchemy.orm import Session

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
from app.services.retrieval_service import retrieve_top_chunks


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


def _build_citations(chunks: list[dict]) -> list[dict]:
    return [
        {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "document_title": item["document_title"],
            "snippet": item["snippet"],
            "page_no": item.get("page_no"),
        }
        for item in chunks[:3]
    ]


def _prepare_rag(db: Session, question: str, provider: str | None) -> tuple[str, dict | None, list[dict], str]:
    fingerprint = knowledge_base_fingerprint(db)
    cached = get_cached_answer(question, provider, fingerprint)
    retrieval_context = [] if cached else retrieve_top_chunks(db, question)
    return fingerprint, cached, retrieval_context, provider or "local"


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
    fingerprint, cached, retrieval_context, _ = _prepare_rag(db, question, provider)

    if cached:
        rag_result = cached
    else:
        rag_result = answer_with_rag(question, retrieval_context, provider)
        set_cached_answer(question, provider, fingerprint, rag_result)

    _persist_answer(db, session, question, rag_result["answer"], rag_result["citations"])

    return AskResponse(
        session_id=session.id,
        answer=rag_result["answer"],
        citations=rag_result["citations"],
        provider_used=rag_result["provider_used"],
    )


def stream_question(
    db: Session,
    user: User,
    question: str,
    session_id: str | None = None,
    provider: str | None = None,
) -> Iterator[str]:
    session = _ensure_session(db, user, session_id, question)
    fingerprint, cached, retrieval_context, _ = _prepare_rag(db, question, provider)
    citations = _build_citations(retrieval_context)

    def encode(event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    yield encode("session", {"session_id": session.id})

    if cached:
        answer = cached["answer"]
        provider_used = cached.get("provider_used", provider or "local")
        citations = cached.get("citations", citations)
        yield encode("citations", {"citations": citations})
        if answer:
            yield encode("token", {"content": answer})
        _persist_answer(db, session, question, answer, citations)
        yield encode("done", {"provider_used": provider_used, "answer": answer, "citations": citations})
        return

    yield encode("citations", {"citations": citations})

    answer_parts: list[str] = []
    stream, provider_used = stream_chat_completion([{"role": "user", "content": question}], retrieval_context, provider)
    try:
        for chunk in stream:
            if not chunk:
                continue
            answer_parts.append(chunk)
            yield encode("token", {"content": chunk})

        answer = "".join(answer_parts).strip()
        rag_result = {
            "answer": answer,
            "citations": citations,
            "provider_used": provider_used,
        }
        set_cached_answer(question, provider, fingerprint, rag_result)
        _persist_answer(db, session, question, answer, citations)
        yield encode("done", {"provider_used": provider_used, "answer": answer, "citations": citations})
    except Exception as exc:
        db.rollback()
        yield encode("error", {"detail": str(exc)})


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
            for message in sorted(session.messages, key=lambda item: item.created_at)
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
