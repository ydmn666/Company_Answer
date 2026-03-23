import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.chat import AskResponse, ChatSessionItem, CitationItem

from base import APITestCase


class ChatAPITestCase(APITestCase):
    def test_ask_question_returns_answer_and_citations(self):
        with patch("app.api.routes.chat.ask_question") as ask_question:
            ask_question.return_value = AskResponse(
                session_id="session-1",
                answer="公司的请假流程需要先提交审批。",
                citations=[
                    CitationItem(
                        chunk_id="chunk-1",
                        document_id="doc-1",
                        document_title="员工手册",
                        snippet="请假前需要先提交审批。",
                        page_no=1,
                        section_title="请假",
                        chunk_index=0,
                    )
                ],
                provider_used="local",
                rewritten_question="公司的请假流程是什么",
            )

            response = self.client.post(
                "/api/chat/ask",
                headers={"Authorization": "Bearer mock-token"},
                json={"question": "公司的请假流程是什么"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], "session-1")
        self.assertTrue(data["answer"])
        self.assertEqual(data["citations"][0]["chunk_id"], "chunk-1")

    def test_list_sessions_returns_existing_sessions(self):
        with patch("app.api.routes.chat.list_sessions") as list_sessions:
            now = datetime.utcnow()
            list_sessions.return_value = [
                ChatSessionItem(
                    id="session-1",
                    title="请假流程",
                    pinned=False,
                    pinned_at=None,
                    created_at=now,
                    updated_at=now,
                    message_count=2,
                )
            ]

            response = self.client.get(
                "/api/chat/sessions",
                headers={"Authorization": "Bearer mock-token"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "session-1")
        self.assertEqual(data[0]["message_count"], 2)

    def test_stream_question_returns_sse_response(self):
        with patch("app.api.routes.chat.stream_question") as stream_question:
            stream_question.return_value = iter(
                [
                    'event: session\ndata: {"session_id":"session-1"}\n\n',
                    'event: done\ndata: {"answer":"done","citations":[],"provider_used":"local"}\n\n',
                ]
            )

            response = self.client.post(
                "/api/chat/ask-stream",
                headers={"Authorization": "Bearer mock-token"},
                json={"question": "测试流式输出"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("event: session", response.text)
        self.assertIn("event: done", response.text)
