from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import LoginResponse, UserInfo
from app.services.security_service import create_token


def _to_user_info(user: User) -> UserInfo:
    # 把数据库用户对象转换成接口返回模型。
    return UserInfo(id=user.id, username=user.username, name=user.full_name, role=user.role)


def login_user(db: Session, username: str, password: str) -> LoginResponse:
    # 当前 V1 是轻量演示登录：
    # 直接比对数据库里的账号密码。
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != password:
        raise ValueError("Invalid username or password")

    return LoginResponse(
        token=create_token(user.id),
        user=_to_user_info(user),
    )


def get_current_user_info(user: User) -> UserInfo:
    return _to_user_info(user)
