import re
from datetime import datetime
from io import BytesIO

import fitz
from docx import Document as DocxDocument
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.documents import (
    DocumentActionResponse,
    DocumentChunkItem,
    DocumentDetailResponse,
    DocumentItem,
    DocumentListResponse,
    UpdateDocumentRequest,
    UploadDocumentResponse,
)
from app.services.ocr_service import extract_text_with_ocr
from app.services.retrieval_service import current_embedding_model_name, generate_embedding, tokenize


HEADING_PATTERN = re.compile(
    r"^(#{1,6}\s+.+|第[一二三四五六七八九十\d]+[章节部分条款].+|[一二三四五六七八九十]+、.+)$"
)
SENTENCE_PATTERN = re.compile(r"(?<=[。！？；.!?;])")


def _token_count(text: str) -> int:
    return len(tokenize(text))


def _normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r\n", "\n").split("\n")]


def _append_block(blocks: list[dict], content: str, section_title: str | None, page_no: int | None) -> None:
    cleaned = content.strip()
    if not cleaned:
        return

    blocks.append(
        {
            "content": cleaned,
            "section_title": section_title,
            "page_no": page_no,
            "chunk_type": "section" if section_title and cleaned == section_title else "paragraph",
        }
    )


def _structured_blocks_from_text(text: str, page_no: int | None = None) -> list[dict]:
    lines = _normalize_lines(text)
    blocks: list[dict] = []
    buffer: list[str] = []
    current_section: str | None = None

    for line in lines:
        if not line:
            _append_block(blocks, "\n".join(buffer), current_section, page_no)
            buffer = []
            continue

        if HEADING_PATTERN.match(line) or (len(line) <= 28 and line.endswith((":", "："))):
            _append_block(blocks, "\n".join(buffer), current_section, page_no)
            buffer = []
            current_section = line
            continue

        buffer.append(line)

    _append_block(blocks, "\n".join(buffer), current_section, page_no)
    return blocks


def _split_long_text(text: str, max_chars: int = 360, overlap: int = 60) -> list[str]:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return [cleaned]

    sentences = [item.strip() for item in SENTENCE_PATTERN.split(cleaned) if item.strip()]
    if len(sentences) <= 1:
        step = max(max_chars - overlap, 80)
        sentences = [cleaned[index:index + max_chars] for index in range(0, len(cleaned), step)]

    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current}{sentence}"
        if current and len(candidate) > max_chars:
            pieces.append(current.strip())
            tail = current[-overlap:] if overlap and len(current) > overlap else current
            current = f"{tail}{sentence}"
            continue
        current = candidate

    if current.strip():
        pieces.append(current.strip())

    return pieces or [cleaned]


def _extract_pdf_with_pymupdf(content: bytes) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    with fitz.open(stream=content, filetype="pdf") as pdf:
        for index, page in enumerate(pdf, start=1):
            page_text = (page.get_text("text") or "").strip()
            if page_text:
                pages.append((index, page_text))
    return pages


def _extract_pdf_with_pypdf(content: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(BytesIO(content))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            pages.append((index, page_text))
    return pages


def _extract_text_blocks(content: bytes, filename: str, content_type: str | None) -> tuple[str, list[dict]]:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if content_type == "application/pdf" or suffix == "pdf":
        page_texts = _extract_pdf_with_pymupdf(content)
        if not page_texts:
            page_texts = _extract_pdf_with_pypdf(content)
        if not page_texts:
            page_texts = extract_text_with_ocr(content)

        if not page_texts:
            fallback = "当前 PDF 未提取到有效文本，文件可能是扫描件或图片型 PDF。"
            return fallback, [{"content": fallback, "section_title": "解析提示", "page_no": None, "chunk_type": "note"}]

        raw_pages = []
        blocks: list[dict] = []
        for page_no, page_text in page_texts:
            raw_pages.append(page_text)
            blocks.extend(_structured_blocks_from_text(page_text, page_no=page_no))
        return "\n\n".join(raw_pages).strip(), blocks

    if content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or suffix == "docx":
        doc = DocxDocument(BytesIO(content))
        raw_text = "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()).strip()
        return raw_text, _structured_blocks_from_text(raw_text)

    raw_text = content.decode("utf-8", errors="ignore").strip()
    return raw_text, _structured_blocks_from_text(raw_text)


def _build_chunk_payloads(raw_text: str, blocks: list[dict]) -> list[dict]:
    source_blocks = blocks or [
        {
            "content": raw_text.strip() or "未能从上传文件中提取有效文本内容。",
            "section_title": None,
            "page_no": None,
            "chunk_type": "paragraph",
        }
    ]
    chunk_payloads: list[dict] = []

    for block in source_blocks:
        for piece in _split_long_text(block["content"]):
            chunk_payloads.append(
                {
                    "content": piece,
                    "section_title": block.get("section_title"),
                    "page_no": block.get("page_no"),
                    "chunk_type": block.get("chunk_type") or "paragraph",
                    "token_count": _token_count(piece),
                }
            )

    return chunk_payloads


def _rebuild_chunks(db: Session, document: Document, chunk_payloads: list[dict]) -> None:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    db.flush()

    created_chunks: list[DocumentChunk] = []
    embedding_model = current_embedding_model_name()
    for index, payload in enumerate(chunk_payloads):
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            section_title=payload["section_title"],
            page_no=payload["page_no"],
            chunk_type=payload["chunk_type"],
            token_count=payload["token_count"],
            content=payload["content"],
            embedding_model=embedding_model,
            embedding=generate_embedding(payload["content"]),
        )
        db.add(chunk)
        db.flush()
        created_chunks.append(chunk)

    for index, chunk in enumerate(created_chunks):
        chunk.prev_chunk_id = created_chunks[index - 1].id if index > 0 else None
        chunk.next_chunk_id = created_chunks[index + 1].id if index < len(created_chunks) - 1 else None


def create_document(
    db: Session,
    title: str,
    filename: str,
    content_type: str | None,
    content: bytes,
    owner_id: str | None = None,
) -> UploadDocumentResponse:
    raw_text, blocks = _extract_text_blocks(content, filename, content_type)
    chunk_payloads = _build_chunk_payloads(raw_text, blocks)
    now = datetime.utcnow()
    document = Document(
        owner_id=owner_id,
        title=title.strip(),
        filename=filename,
        content_type=content_type,
        status="processing",
        summary=(raw_text[:220] if raw_text else "未提取到有效文本。"),
        source_text=raw_text,
        chunk_count=len(chunk_payloads),
        updated_at=now,
    )
    db.add(document)
    db.flush()

    _rebuild_chunks(db, document, chunk_payloads)
    document.status = "indexed"
    document.updated_at = now
    db.commit()
    db.refresh(document)
    return UploadDocumentResponse(
        id=document.id,
        title=document.title,
        status=document.status,
        chunk_count=document.chunk_count,
    )


def list_documents(db: Session, query: str | None = None) -> DocumentListResponse:
    documents_query = db.query(Document)
    if query:
        like = f"%{query.strip()}%"
        documents_query = documents_query.filter(
            (Document.title.ilike(like)) | (Document.filename.ilike(like)) | (Document.summary.ilike(like))
        )

    items = documents_query.order_by(Document.updated_at.desc(), Document.created_at.desc()).all()
    return DocumentListResponse(items=[DocumentItem.model_validate(item) for item in items])


def get_document(db: Session, document_id: str) -> DocumentDetailResponse | None:
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
                section_title=chunk.section_title,
                page_no=chunk.page_no,
                chunk_type=chunk.chunk_type,
                token_count=chunk.token_count,
                content=chunk.content,
            )
            for chunk in sorted(document.chunks, key=lambda item: item.chunk_index)
        ],
    )


def update_document(db: Session, document_id: str, payload: UpdateDocumentRequest) -> DocumentDetailResponse | None:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return None

    if payload.title is not None:
        document.title = payload.title.strip() or document.title
    if payload.summary is not None:
        document.summary = payload.summary.strip()
    document.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    return get_document(db, document_id)


def delete_document(db: Session, document_id: str) -> DocumentActionResponse | None:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return None

    db.delete(document)
    db.commit()
    return DocumentActionResponse(id=document_id, message="Document deleted")
