from datetime import datetime

from pydantic import BaseModel


class DocumentItem(BaseModel):
    # 管理文档页单条记录。
    id: str
    title: str
    filename: str
    status: str
    summary: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]


class DocumentChunkItem(BaseModel):
    # 文档详情页中的单个切片。
    id: str
    chunk_index: int
    content: str


class DocumentDetailResponse(DocumentItem):
    # 文档详情会额外带 content_type 和切片列表。
    content_type: str | None = None
    chunks: list[DocumentChunkItem]


class UploadDocumentResponse(BaseModel):
    # 上传完成后前端所需的最小回执。
    id: str
    title: str
    status: str
    chunk_count: int
