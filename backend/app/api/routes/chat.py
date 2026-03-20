from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import AskRequest, AskResponse, ChatSessionDetail, ChatSessionItem
from app.services.chat_service import ask_question, get_session, list_sessions

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    # 前端提问后，这里串起检索、RAG、落库、返回引用。
    return ask_question(db, current_user, payload.question, payload.session_id, payload.provider)


@router.get("/sessions", response_model=list[ChatSessionItem])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSessionItem]:
    # 左侧历史会话列表。
    return list_sessions(db, current_user)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionDetail:
    # 某条历史会话的完整聊天记录。
    session = get_session(db, current_user, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
