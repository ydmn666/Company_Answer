from datetime import datetime

from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    snippet: str
    page_no: int | None = None
    section_title: str | None = None
    chunk_index: int | None = None


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None
    provider: str | None = None


class AskResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[CitationItem]
    provider_used: str
    rewritten_question: str | None = None


class ChatSessionItem(BaseModel):
    id: str
    title: str
    pinned: bool
    pinned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int

    model_config = {"from_attributes": True}


class ChatMessageItem(BaseModel):
    id: str
    role: str
    content: str
    citations: list[CitationItem] = Field(default_factory=list)
    provider_used: str | None = None
    rewritten_question: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetail(BaseModel):
    id: str
    title: str
    pinned: bool
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageItem]


class UpdateSessionRequest(BaseModel):
    title: str | None = None
    pinned: bool | None = None


class SessionActionResponse(BaseModel):
    id: str
    message: str
