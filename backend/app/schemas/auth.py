from pydantic import BaseModel


# 这些 schema 是前后端之间的“数据契约”。
class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: str
    username: str
    name: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserInfo
