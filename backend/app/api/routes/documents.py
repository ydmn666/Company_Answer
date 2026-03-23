from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.documents import (
    DocumentActionResponse,
    DocumentBatchDeleteRequest,
    DocumentBatchDeleteResponse,
    DocumentChunkDetailResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    UpdateDocumentRequest,
    UploadDocumentFailureItem,
    UploadDocumentResponse,
    UploadDocumentsResponse,
)
from app.services.document_service import (
    batch_delete_documents,
    create_document,
    delete_document,
    get_chunk_detail,
    get_document,
    get_source_file_path,
    list_documents,
    update_document,
)

router = APIRouter()


@router.post("/upload", response_model=UploadDocumentsResponse)
async def upload_document(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UploadDocumentsResponse:
    results: list[UploadDocumentResponse] = []
    failed_items: list[UploadDocumentFailureItem] = []

    for file in files:
        content = await file.read()
        filename = file.filename or "uploaded.bin"
        effective_title = filename.rsplit(".", 1)[0]
        try:
            results.append(
                create_document(
                    db=db,
                    title=effective_title,
                    filename=filename,
                    content_type=file.content_type,
                    content=content,
                    owner_id=current_user.id,
                )
            )
        except ValueError as exc:
            failed_items.append(
                UploadDocumentFailureItem(
                    filename=filename,
                    title=effective_title,
                    message=str(exc),
                )
            )

    if not results and failed_items:
        raise HTTPException(status_code=409, detail=failed_items[0].message)

    return UploadDocumentsResponse(items=results, failed_items=failed_items)


@router.get("", response_model=DocumentListResponse)
def get_documents(
    query: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentListResponse:
    return list_documents(db, query, file_type)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_by_id(
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    document = get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/chunks/{chunk_id}", response_model=DocumentChunkDetailResponse)
def get_document_chunk_detail(
    chunk_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentChunkDetailResponse:
    chunk = get_chunk_detail(db, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


@router.get("/{document_id}/download")
def download_document_source(
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FileResponse:
    result = get_source_file_path(db, document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Source file not found")

    document, path = result
    return FileResponse(path=path, filename=document.filename, media_type=document.content_type or "application/octet-stream")


@router.patch("/{document_id}", response_model=DocumentDetailResponse)
def patch_document(
    document_id: str,
    payload: UpdateDocumentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentDetailResponse:
    document = update_document(db, document_id, payload)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", response_model=DocumentActionResponse)
def remove_document(
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentActionResponse:
    result = delete_document(db, document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.post("/batch-delete", response_model=DocumentBatchDeleteResponse)
def remove_documents(
    payload: DocumentBatchDeleteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentBatchDeleteResponse:
    return batch_delete_documents(db, payload.ids)
