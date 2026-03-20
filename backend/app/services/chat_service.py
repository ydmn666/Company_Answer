import json
import math
import re

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.schemas.chat import AskResponse, ChatMessageItem, ChatSessionDetail, ChatSessionItem
from app.services.llm_service import answer_with_rag, generate_embedding


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")


def _tokenize_for_rank(text: str) -> set[str]:
    # 统一拆词，给检索排序打基础。
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _rank_terms(text: str) -> set[str]:
    # 中文额外展开 2~4 字子串，提升短词召回率。
    terms = _tokenize_for_rank(text)
    expanded = set(terms)
    for term in terms:
        if re.fullmatch(r"[\u4e00-\u9fff]+", term) and len(term) >= 2:
            max_size = min(4, len(term))
            for size in range(2, max_size + 1):
                for index in range(0, len(term) - size + 1):
                    expanded.add(term[index:index + size])
    return expanded


def _cosine_distance(left: list[float] | None, right: list[float]) -> float:
    # 用余弦距离比较“问题向量”和“切片向量”的接近程度。
    if left is None or len(left) == 0:
        return 1.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    similarity = numerator / (left_norm * right_norm)
    return 1.0 - similarity


def _ensure_session(db: Session, user: User, session_id: str | None, question: str) -> ChatSession:
    # 新对话第一次发言时，在这里自动建 session。
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
            .first()
        )
        if session:
            return session

    session = ChatSession(user_id=user.id, title=question[:60] or "新会话")
    db.add(session)
    db.flush()
    return session


def _retrieve_top_chunks(db: Session, question: str, top_k: int = 3) -> list[dict]:
    # 当前 V1 采用轻量混合检索：
    # 关键词重叠 + 标题命中 + embedding 相似度。
    query_embedding = generate_embedding(question)
    question_terms = _rank_terms(question)
    chunks = db.query(DocumentChunk).all()
    ranked_chunks: list[tuple[float, DocumentChunk]] = []

    for chunk in chunks:
        document_title = chunk.document.title if chunk.document else ""
        chunk_terms = _rank_terms(f"{document_title} {chunk.content}")
        lexical_overlap = len(question_terms & chunk_terms)
        title_boost = 4 if any(term in document_title.lower() for term in question_terms) else 0
        direct_match_boost = 2 if any(term in chunk.content.lower() for term in question_terms) else 0
        semantic_distance = _cosine_distance(chunk.embedding, query_embedding)
        score = lexical_overlap * 3 + title_boost + direct_match_boost - float(semantic_distance)
        ranked_chunks.append((score, chunk))

    ranked_chunks.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document.id,
            "document_title": chunk.document.title,
            "snippet": chunk.content[:220],
        }
        for _, chunk in ranked_chunks[:top_k]
    ]


def ask_question(
    db: Session,
    user: User,
    question: str,
    session_id: str | None = None,
    provider: str | None = None,
) -> AskResponse:
    # 从“前端提问”到“后端返回答案”的主链路。
    session = _ensure_session(db, user, session_id, question)
    retrieval_context = _retrieve_top_chunks(db, question)
    rag_result = answer_with_rag(question, retrieval_context, provider)

    # 问题和回答都要落库，供前端历史会话回放。
    db.add(ChatMessage(session_id=session.id, role="user", content=question))
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=rag_result["answer"],
            citations_json=json.dumps(rag_result["citations"], ensure_ascii=False),
        )
    )
    db.commit()

    return AskResponse(
        session_id=session.id,
        answer=rag_result["answer"],
        citations=rag_result["citations"],
        provider_used=rag_result["provider_used"],
    )


def list_sessions(db: Session, user: User) -> list[ChatSessionItem]:
    # 左侧历史会话列表数据。
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [ChatSessionItem.model_validate(item) for item in sessions]


def get_session(db: Session, user: User, session_id: str) -> ChatSessionDetail | None:
    # 某条历史会话的完整明细。
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
        created_at=session.created_at,
        messages=[
            ChatMessageItem.model_validate(message)
            for message in sorted(session.messages, key=lambda item: item.created_at)
        ],
    )
