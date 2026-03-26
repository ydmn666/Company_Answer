import logging

from app.core.logging_utils import log_event
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import LoginResponse, UserInfo
from app.services.security_service import create_token

logger = logging.getLogger(__name__)


# å°æ°æ®åºç¨æ·å¯¹è±¡è½¬æ¢ä¸ºæ¥å£è¿åæéçç¨æ·ä¿¡æ¯ç»æã
def _to_user_info(user: User) -> UserInfo:
    # 把数据库用户对象转换成接口返回模型。
    return UserInfo(id=user.id, username=user.username, name=user.full_name, role=user.role)


# æ ¡éªç¨æ·åå¯ç å¹¶çæç»å½ tokenã
def login_user(db: Session, username: str, password: str) -> LoginResponse:
    # 当前 V1 是轻量演示登录：
    # 直接比对数据库里的账号密码。
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != password:
        log_event(logger, "auth.login.failed", username=username)
        raise ValueError("Invalid username or password")

    log_event(logger, "auth.login.succeeded", user_id=user.id, username=user.username, role=user.role)
    return LoginResponse(
        token=create_token(user.id),
        user=_to_user_info(user),
    )


# è¿åå½åå·²ç»å½ç¨æ·çåºç¡èµæã
def get_current_user_info(user: User) -> UserInfo:
    return _to_user_info(user)
