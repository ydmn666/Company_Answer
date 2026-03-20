from io import BytesIO

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.documents import (
    DocumentChunkItem,
    DocumentDetailResponse,
    DocumentItem,
    DocumentListResponse,
    UploadDocumentResponse,
)
from app.services.llm_service import generate_embedding


def _extract_text(content: bytes, filename: str, content_type: str | None) -> str:
    # 文档解析入口：PDF 用 pypdf，其他文件按 utf-8 文本处理。
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if content_type == "application/pdf" or suffix == "pdf":
        reader = PdfReader(BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()

    return content.decode("utf-8", errors="ignore").strip()


def _chunk_content(raw_text: str, chunk_size: int = 220, overlap: int = 40) -> list[str]:
    # 切片是知识检索的基础。
    text = raw_text.strip() or "未能从上传文件中解析出文本内容。"
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def create_document(
    db: Session,
    title: str,
    filename: str,
    content_type: str | None,
    content: bytes,
    owner_id: str | None = None,
) -> UploadDocumentResponse:
    # 上传 -> 解析 -> 切片 -> 向量化 -> 写库。
    raw_text = _extract_text(content, filename, content_type)
    chunks = _chunk_content(raw_text)
    document = Document(
        owner_id=owner_id,
        title=title,
        filename=filename,
        content_type=content_type,
        status="processing",
        summary=(raw_text[:180] if raw_text else "未提取到有效文本。"),
        chunk_count=len(chunks),
    )
    db.add(document)
    db.flush()

    for index, chunk_text in enumerate(chunks):
        # 每个切片都存一份 embedding，后续检索按切片做。
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_text,
                embedding=generate_embedding(chunk_text),
            )
        )

    document.status = "indexed"
    db.commit()
    db.refresh(document)
    return UploadDocumentResponse(
        id=document.id,
        title=document.title,
        status=document.status,
        chunk_count=document.chunk_count,
    )


def list_documents(db: Session) -> DocumentListResponse:
    # 管理文档页列表数据。
    items = db.query(Document).order_by(Document.created_at.desc()).all()
    return DocumentListResponse(items=[DocumentItem.model_validate(item) for item in items])


def get_document(db: Session, document_id: str) -> DocumentDetailResponse | None:
    # 文档详情页 / 引用详情的数据组装。
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return None

    return DocumentDetailResponse(
        **DocumentItem.model_validate(document).model_dump(),
        content_type=document.content_type,
        chunks=[
            DocumentChunkItem(
                id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
            )
            for chunk in sorted(document.chunks, key=lambda item: item.chunk_index)
        ],
    )
