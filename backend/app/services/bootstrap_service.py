from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.retrieval_service import current_embedding_model_name, generate_embedding, tokenize


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


def _ensure_document(
    db: Session,
    owner_id: str,
    title: str,
    filename: str,
    content: str,
) -> None:
    existing = db.query(Document).filter(Document.title == title, Document.filename == filename).first()
    if existing:
        return

    document = Document(
        owner_id=owner_id,
        title=title,
        filename=filename,
        content_type="text/plain",
        status="indexed",
        summary=content[:140],
        source_text=content,
        chunk_count=1,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            chunk_type="paragraph",
            token_count=len(tokenize(content)),
            embedding_model=current_embedding_model_name(),
            content=content,
            embedding=generate_embedding(content),
        )
    )


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
        if "?" not in session.title and "閿" not in session.title:
            continue
        first_user_message = next(
            (item for item in sorted(session.messages, key=lambda value: value.created_at) if item.role == "user"),
            None,
        )
        if first_user_message and first_user_message.content:
            session.title = first_user_message.content[:60]


def seed_demo_data(db: Session) -> None:
    admin = _ensure_user(db, "admin", "System Admin", "admin")
    employee = _ensure_user(db, "employee", "Knowledge Employee", "employee")

    _ensure_document(
        db,
        admin.id,
        "员工安全制度",
        "security-policy.txt",
        "企业员工必须为核心系统启用多因素认证。发现安全事件后，应在30分钟内完成上报。工程师访问生产系统前需要完成权限审批。",
    )
    _ensure_document(
        db,
        admin.id,
        "IT 服务台手册",
        "helpdesk-handbook.txt",
        "服务台执行密码重置前必须核验员工身份。所有高权限操作都需要工单编号和审计日志。",
    )
    _ensure_session(db, employee.id)
    _repair_session_titles(db)
    db.commit()
