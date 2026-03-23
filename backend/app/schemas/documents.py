from datetime import datetime

from pydantic import BaseModel, Field


class SourcePageItem(BaseModel):
    page_no: int
    content: str


class DocumentItem(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    source_file_path: str | None = None
    source_file_size: int | None = None
    source_file_exists: bool = False
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
    source_text: str
    source_pages: list[SourcePageItem] = Field(default_factory=list)
    chunks: list[DocumentChunkItem]


class ChunkNeighborItem(BaseModel):
    id: str
    chunk_index: int
    section_title: str | None = None
    page_no: int | None = None
    content: str


class DocumentChunkDetailResponse(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    filename: str
    file_type: str
    content_type: str | None = None
    page_no: int | None = None
    section_title: str | None = None
    chunk_index: int
    snippet: str
    content: str
    previous_chunk: ChunkNeighborItem | None = None
    next_chunk: ChunkNeighborItem | None = None
    source_text: str
    source_page_content: str | None = None
    source_file_exists: bool = False


class DocumentBatchDeleteRequest(BaseModel):
    ids: list[str]


class DocumentBatchDeleteResponse(BaseModel):
    ids: list[str]
    deleted_count: int
    message: str


class UploadDocumentResponse(BaseModel):
    id: str
    title: str
    status: str
    chunk_count: int


class UploadDocumentFailureItem(BaseModel):
    filename: str
    title: str
    message: str


class UploadDocumentsResponse(BaseModel):
    items: list[UploadDocumentResponse]
    failed_items: list[UploadDocumentFailureItem] = Field(default_factory=list)


class UpdateDocumentRequest(BaseModel):
    title: str | None = None
    summary: str | None = None


class DocumentActionResponse(BaseModel):
    id: str
    message: str
