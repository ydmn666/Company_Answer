from datetime import datetime

from pydantic import BaseModel


class DocumentItem(BaseModel):
    id: str
    title: str
    filename: str
    status: str
    summary: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]


class DocumentChunkItem(BaseModel):
    id: str
    chunk_index: int
    section_title: str | None = None
    page_no: int | None = None
    chunk_type: str
    token_count: int
    content: str


class DocumentDetailResponse(DocumentItem):
    content_type: str | None = None
    chunks: list[DocumentChunkItem]


class UploadDocumentResponse(BaseModel):
    id: str
    title: str
    status: str
    chunk_count: int


class UpdateDocumentRequest(BaseModel):
    title: str | None = None
    summary: str | None = None


class DocumentActionResponse(BaseModel):
    id: str
    message: str
