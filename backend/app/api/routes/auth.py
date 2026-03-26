from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo
from app.services.auth_service import get_current_user_info, login_user

router = APIRouter()


# å¤çç»å½è¯·æ±å¹¶è¿å token ä¸å½åç¨æ·ä¿¡æ¯ã
@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    # 登录成功后返回 token + 当前用户信息。
    try:
        return login_user(db, payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# è¿åå½åç»å½ç¨æ·çåºç¡èµæï¼ä¾åç«¯æ¢å¤ç»å½ç¶æã
@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(get_current_user)) -> UserInfo:
    # 前端刷新后可用这个接口恢复当前用户信息。
    return get_current_user_info(user)
