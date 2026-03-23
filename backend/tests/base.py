import sys
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
import types

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if "rank_bm25" not in sys.modules:
    rank_bm25_stub = types.ModuleType("rank_bm25")

    class _BM25Okapi:
        def __init__(self, *_args, **_kwargs):
            pass

        def get_scores(self, _query_tokens):
            return []

    rank_bm25_stub.BM25Okapi = _BM25Okapi
    sys.modules["rank_bm25"] = rank_bm25_stub

if "fitz" not in sys.modules:
    fitz_stub = types.ModuleType("fitz")

    class _DummyDocument:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter([])

    fitz_stub.open = lambda *args, **kwargs: _DummyDocument()
    fitz_stub.Matrix = lambda *args, **kwargs: None
    sys.modules["fitz"] = fitz_stub

if "pypdf" not in sys.modules:
    pypdf_stub = types.ModuleType("pypdf")

    class _PdfReader:
        def __init__(self, *_args, **_kwargs):
            self.pages = []

    pypdf_stub.PdfReader = _PdfReader
    sys.modules["pypdf"] = pypdf_stub

if "docx" not in sys.modules:
    docx_stub = types.ModuleType("docx")

    class _DocxDocument:
        def __init__(self, *_args, **_kwargs):
            self.paragraphs = []

    docx_stub.Document = _DocxDocument
    sys.modules["docx"] = docx_stub

if "PIL" not in sys.modules:
    pil_stub = types.ModuleType("PIL")
    image_stub = types.ModuleType("PIL.Image")
    image_stub.open = lambda *_args, **_kwargs: None
    pil_stub.Image = image_stub
    sys.modules["PIL"] = pil_stub
    sys.modules["PIL.Image"] = image_stub

from app.api.deps import get_current_user, get_db, require_admin
from app.main import app


@asynccontextmanager
async def _noop_lifespan(_: object):
    yield


class APITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_lifespan = app.router.lifespan_context
        app.router.lifespan_context = _noop_lifespan

    @classmethod
    def tearDownClass(cls):
        app.router.lifespan_context = cls._original_lifespan

    def setUp(self):
        self.dummy_db = object()
        self.admin_user = SimpleNamespace(
            id="admin-1",
            username="admin",
            full_name="System Admin",
            role="admin",
        )
        self.employee_user = SimpleNamespace(
            id="employee-1",
            username="employee",
            full_name="Knowledge Employee",
            role="employee",
        )
        app.dependency_overrides[get_db] = lambda: self.dummy_db
        app.dependency_overrides[get_current_user] = lambda: self.employee_user
        app.dependency_overrides[require_admin] = lambda: self.admin_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
