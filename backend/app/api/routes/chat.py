from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    AskRequest,
    AskResponse,
    ChatSessionDetail,
    ChatSessionItem,
    SessionActionResponse,
    UpdateSessionRequest,
)
from app.services.chat_service import (
    ask_question,
    delete_session,
    get_session,
    list_sessions,
    stream_question,
    update_session,
)

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    return ask_question(db, current_user, payload.question, payload.session_id, payload.provider)


@router.post("/ask-stream")
def ask_stream(
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    stream = stream_question(db, current_user, payload.question, payload.session_id, payload.provider)
    return StreamingResponse(stream, media_type="text/event-stream")


@router.get("/sessions", response_model=list[ChatSessionItem])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSessionItem]:
    return list_sessions(db, current_user)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionDetail:
    session = get_session(db, current_user, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/sessions/{session_id}", response_model=ChatSessionDetail)
def patch_session(
    session_id: str,
    payload: UpdateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionDetail:
    session = update_session(db, current_user, session_id, payload)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}", response_model=SessionActionResponse)
def remove_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionActionResponse:
    result = delete_session(db, current_user, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
