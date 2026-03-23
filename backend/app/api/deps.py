from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.logging_utils import set_request_context
from app.db.session import get_db
from app.models.user import User
from app.services.security_service import decode_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    # 前端 axios 会自动把 token 放进 Authorization 头里，
    # 这里负责把 Bearer token 还原成当前用户。
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.replace("Bearer ", "", 1)
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    set_request_context(user_id=user.id)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    # 管理员专用接口的权限检查。
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
