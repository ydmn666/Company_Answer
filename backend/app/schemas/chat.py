from datetime import datetime

from pydantic import BaseModel


class CitationItem(BaseModel):
    # 前端右侧“引用依据”面板按这个结构渲染。
    chunk_id: str
    document_id: str
    document_title: str
    snippet: str


class AskRequest(BaseModel):
    # session_id 为空时表示新对话。
    # provider 用于切换本地 / DeepSeek / Kimi。
    question: str
    session_id: str | None = None
    provider: str | None = None


class AskResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[CitationItem]
    provider_used: str


class ChatSessionItem(BaseModel):
    # 左侧历史会话列表项。
    id: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageItem(BaseModel):
    # 单条聊天消息返回模型。
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetail(BaseModel):
    # 某条会话的完整明细。
    id: str
    title: str
    created_at: datetime
    messages: list[ChatMessageItem]
