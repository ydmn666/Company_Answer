import logging

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.logging_utils import log_event
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.retrieval_service import current_embedding_model_name, generate_embedding


DEMO_DOCUMENT_FILENAMES = {"security-policy.txt", "helpdesk-handbook.txt"}
logger = logging.getLogger(__name__)


def _trace(event: str, **payload) -> None:
    log_event(logger, event, **payload)


def _ensure_user(
    db: Session,
    username: str,
    full_name: str,
    role: str,
    password: str = "password",
) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            full_name=full_name,
            password_hash=password,
            role=role,
        )
        db.add(user)
        db.flush()
        return user

    user.full_name = full_name
    user.password_hash = password
    user.role = role
    db.flush()
    return user


def _ensure_session(db: Session, user_id: str) -> None:
    existing = (
        db.query(ChatSession)
        .filter(ChatSession.title == "核心系统访问要求", ChatSession.user_id == user_id)
        .first()
    )
    if existing:
        return

    session = ChatSession(user_id=user_id, title="核心系统访问要求")
    db.add(session)
    db.flush()
    db.add(ChatMessage(session_id=session.id, role="user", content="核心系统访问需要满足什么要求？"))
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content="核心系统访问需要启用多因素认证，访问生产系统前还需要完成权限审批。",
            citations_json="[]",
        )
    )


def _repair_session_titles(db: Session) -> None:
    sessions = db.query(ChatSession).all()
    for session in sessions:
        if "?" not in session.title and "闁" not in session.title:
            continue
        first_user_message = next(
            (item for item in sorted(session.messages, key=lambda value: value.created_at) if item.role == "user"),
            None,
        )
        if first_user_message and first_user_message.content:
            session.title = first_user_message.content[:60]


def _remove_demo_documents(db: Session) -> None:
    demo_documents = (
        db.query(Document)
        .filter(Document.filename.in_(DEMO_DOCUMENT_FILENAMES))
        .all()
    )
    if not demo_documents:
        return

    _trace("demo_documents.remove_start", count=len(demo_documents))
    for document in demo_documents:
        db.delete(document)
    db.flush()
    _trace("demo_documents.remove_done", count=len(demo_documents))


def _backfill_chunk_embeddings(db: Session) -> None:
    current_model = current_embedding_model_name()
    stale_chunks = (
        db.query(DocumentChunk)
        .filter(
            (DocumentChunk.embedding.is_(None))
            | (DocumentChunk.embedding_model.is_(None))
            | (DocumentChunk.embedding_model != current_model)
        )
        .all()
    )
    if not stale_chunks:
        _trace("embedding_backfill.skip", model=current_model, chunks=0)
        return

    _trace("embedding_backfill.start", model=current_model, chunks=len(stale_chunks))
    for chunk in stale_chunks:
        db.execute(
            update(DocumentChunk)
            .where(DocumentChunk.id == chunk.id)
            .values(
                embedding=generate_embedding(chunk.content),
                embedding_model=current_model,
            )
            .execution_options(synchronize_session=False)
        )
    db.flush()
    _trace("embedding_backfill.done", model=current_model, chunks=len(stale_chunks))


def seed_demo_data(db: Session) -> None:
    _ensure_user(db, "admin", "System Admin", "admin")
    _ensure_user(db, "admin2", "Operations Admin", "admin")
    employee = _ensure_user(db, "employee", "Knowledge Employee", "employee")

    _remove_demo_documents(db)
    _ensure_session(db, employee.id)
    _repair_session_titles(db)
    _backfill_chunk_embeddings(db)
    db.commit()
