from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.documents import DocumentDetailResponse, DocumentListResponse, UploadDocumentResponse
from app.services.document_service import create_document, get_document, list_documents

router = APIRouter()


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UploadDocumentResponse:
    # “知识入库链路”入口：上传 -> 解析 -> 切片 -> 向量化 -> 写库。
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
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentListResponse:
    # 管理文档页列表数据。
    return list_documents(db)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_by_id(
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    # 文档详情抽屉 / 引用详情都从这里取数。
    document = get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
