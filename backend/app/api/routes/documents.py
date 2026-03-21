from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.documents import (
    DocumentActionResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    UpdateDocumentRequest,
    UploadDocumentResponse,
)
from app.services.document_service import (
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document,
)

router = APIRouter()


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UploadDocumentResponse:
    content = await file.read()
    return create_document(
        db=db,
        title=title,
        filename=file.filename or "uploaded.bin",
        content_type=file.content_type,
        content=content,
        owner_id=current_user.id,
    )


@router.get("", response_model=DocumentListResponse)
def get_documents(
    query: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentListResponse:
    return list_documents(db, query)


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
