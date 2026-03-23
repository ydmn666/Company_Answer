import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.documents import (
    DocumentActionResponse,
    DocumentBatchDeleteResponse,
    DocumentChunkDetailResponse,
    DocumentChunkItem,
    DocumentDetailResponse,
    DocumentItem,
    DocumentListResponse,
    UploadDocumentResponse,
)

from base import APITestCase


def _document_item() -> DocumentItem:
    now = datetime.utcnow()
    return DocumentItem(
        id="doc-1",
        title="员工手册",
        filename="employee-handbook.txt",
        file_type="TXT",
        source_file_path="backend/data/source_files/doc-1/employee-handbook.txt",
        source_file_size=128,
        source_file_exists=True,
        status="indexed",
        summary="员工手册摘要",
        chunk_count=2,
        created_at=now,
        updated_at=now,
    )


class DocumentsAPITestCase(APITestCase):
    def test_upload_document_returns_index_result(self):
        with patch("app.api.routes.documents.create_document") as create_document:
            create_document.return_value = UploadDocumentResponse(
                id="doc-1",
                title="employee-handbook",
                status="indexed",
                chunk_count=2,
            )

            response = self.client.post(
                "/api/documents/upload",
                headers={"Authorization": "Bearer mock-token"},
                data={"title": "员工手册"},
                files=[("files", ("employee-handbook.txt", b"company handbook", "text/plain"))],
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["status"], "indexed")
        self.assertEqual(data["items"][0]["chunk_count"], 2)

    def test_list_documents_supports_type_filter(self):
        with patch("app.api.routes.documents.list_documents") as list_documents:
            list_documents.return_value = DocumentListResponse(items=[_document_item()])

            response = self.client.get(
                "/api/documents",
                params={"file_type": "TXT"},
                headers={"Authorization": "Bearer mock-token"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["file_type"], "TXT")

    def test_get_document_detail_returns_source_text_and_chunks(self):
        item = _document_item()
        with patch("app.api.routes.documents.get_document") as get_document:
            get_document.return_value = DocumentDetailResponse(
                **item.model_dump(),
                content_type="text/plain",
                source_text="员工手册原文",
                chunks=[
                    DocumentChunkItem(
                        id="chunk-1",
                        chunk_index=0,
                        section_title="入职",
                        page_no=None,
                        chunk_type="paragraph",
                        token_count=20,
                        content="请按流程提交入职资料。",
                    )
                ],
            )

            response = self.client.get(
                "/api/documents/doc-1",
                headers={"Authorization": "Bearer mock-token"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "员工手册")
        self.assertEqual(data["source_text"], "员工手册原文")
        self.assertEqual(data["chunks"][0]["id"], "chunk-1")

    def test_get_chunk_detail_returns_context(self):
        with patch("app.api.routes.documents.get_chunk_detail") as get_chunk_detail:
            get_chunk_detail.return_value = DocumentChunkDetailResponse(
                chunk_id="chunk-1",
                document_id="doc-1",
                document_title="员工手册",
                filename="employee-handbook.txt",
                file_type="TXT",
                content_type="text/plain",
                page_no=None,
                section_title="入职",
                chunk_index=0,
                snippet="请按流程提交入职资料。",
                content="请按流程提交入职资料。",
                previous_chunk=None,
                next_chunk=None,
                source_text="员工手册原文",
                source_page_content=None,
                source_file_exists=True,
            )

            response = self.client.get(
                "/api/documents/chunks/chunk-1",
                headers={"Authorization": "Bearer mock-token"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["chunk_id"], "chunk-1")
        self.assertEqual(data["document_id"], "doc-1")
        self.assertTrue(data["source_file_exists"])

    def test_batch_delete_documents_returns_deleted_count(self):
        with patch("app.api.routes.documents.batch_delete_documents") as batch_delete_documents:
            batch_delete_documents.return_value = DocumentBatchDeleteResponse(
                ids=["doc-1", "doc-2"],
                deleted_count=2,
                message="Deleted 2 documents",
            )

            response = self.client.post(
                "/api/documents/batch-delete",
                headers={"Authorization": "Bearer mock-token"},
                json={"ids": ["doc-1", "doc-2"]},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["deleted_count"], 2)
        self.assertEqual(data["ids"], ["doc-1", "doc-2"])

    def test_delete_document_returns_action_message(self):
        with patch("app.api.routes.documents.delete_document") as delete_document:
            delete_document.return_value = DocumentActionResponse(id="doc-1", message="Document deleted")

            response = self.client.delete(
                "/api/documents/doc-1",
                headers={"Authorization": "Bearer mock-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Document deleted")
