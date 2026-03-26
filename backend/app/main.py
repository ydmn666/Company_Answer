import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import chat_message, chat_session, document, document_chunk, user  # noqa: F401
from app.core.logging_utils import clear_request_context, configure_logging, log_event, set_request_context
from app.services.health_service import health_snapshot
from app.services.bootstrap_service import seed_demo_data

configure_logging()
logger = logging.getLogger(__name__)


# å¯å¨æ¶ä¸ºæ§è¡¨è¡¥é½ç¼ºå¤±å­æ®µï¼å¼å®¹å·²ææ°æ®åºç»æã
def _ensure_column(inspector, table_name: str, column_name: str, definition: str) -> None:
    if not inspector.has_table(table_name):
        return

    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        return

    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


# ç»ä¸å¤çå¯å¨æ¶çè½»éçº§è¡¨ç»æå¼å®¹ååå²æ°æ®ä¿®å¤ã
def ensure_schema_compatibility() -> None:
    inspector = inspect(engine)

    _ensure_column(inspector, "users", "role", "VARCHAR(30) NOT NULL DEFAULT 'employee'")
    _ensure_column(inspector, "documents", "source_text", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(inspector, "documents", "updated_at", "TIMESTAMP NULL")
    _ensure_column(inspector, "documents", "file_type", "VARCHAR(20) NOT NULL DEFAULT 'TXT'")
    _ensure_column(inspector, "documents", "source_file_path", "TEXT NULL")
    _ensure_column(inspector, "documents", "source_file_size", "BIGINT NULL")
    _ensure_column(inspector, "documents", "source_pages_json", "TEXT NULL")
    _ensure_column(inspector, "document_chunks", "section_title", "VARCHAR(255) NULL")
    _ensure_column(inspector, "document_chunks", "page_no", "INTEGER NULL")
    _ensure_column(inspector, "document_chunks", "chunk_type", "VARCHAR(30) NOT NULL DEFAULT 'paragraph'")
    _ensure_column(inspector, "document_chunks", "prev_chunk_id", "VARCHAR(36) NULL")
    _ensure_column(inspector, "document_chunks", "next_chunk_id", "VARCHAR(36) NULL")
    _ensure_column(inspector, "document_chunks", "token_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(inspector, "document_chunks", "embedding_model", "VARCHAR(120) NULL")
    _ensure_column(inspector, "chat_sessions", "pinned", "BOOLEAN NOT NULL DEFAULT FALSE")
    _ensure_column(inspector, "chat_sessions", "pinned_at", "TIMESTAMP NULL")
    _ensure_column(inspector, "chat_sessions", "updated_at", "TIMESTAMP NULL")

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector"))
        connection.execute(text("UPDATE documents SET updated_at = created_at WHERE updated_at IS NULL"))
        connection.execute(
            text(
                """
                UPDATE documents
                SET file_type = CASE
                    WHEN lower(filename) LIKE '%.pdf' THEN 'PDF'
                    WHEN lower(filename) LIKE '%.docx' THEN 'DOCX'
                    ELSE 'TXT'
                END
                WHERE file_type IS NULL OR file_type = ''
                """
            )
        )
        connection.execute(text("UPDATE chat_sessions SET updated_at = created_at WHERE updated_at IS NULL"))


@asynccontextmanager
# ç®¡çåºç¨å¯å¨åå³é­æµç¨ï¼å®æå»ºè¡¨ãå¼å®¹ä¿®å¤åæ¼ç¤ºæ°æ®åå§åã
async def lifespan(_: FastAPI):
    log_event(logger, "app.startup.begin", app_env=settings.app_env)
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()

    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    log_event(logger, "app.startup.ready")
    yield
    log_event(logger, "app.shutdown.complete")


app = FastAPI(
    title="Enterprise Knowledge Retrieval API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.middleware("http")
# ä¸ºæ¯ä¸ª HTTP è¯·æ±è¡¥åé¾è·¯æ¥å¿ãè¯·æ±æ è¯åèæ¶ç»è®¡ã
async def request_logging_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = time.perf_counter()
    user_id = None
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        user_id = "authenticated"

    set_request_context(request_id=request_id, user_id=user_id)
    log_event(
        logger,
        "http.request.start",
        method=request.method,
        path=request.url.path,
        query=str(request.url.query or ""),
        client=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log_event(
            logger,
            "http.request.complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response
    except Exception:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            logger,
            "http.request.error",
            level=logging.ERROR,
            method=request.method,
            path=request.url.path,
            elapsed_ms=elapsed_ms,
        )
        raise
    finally:
        clear_request_context()


@app.get("/health")
# æä¾ç³»ç»å¥åº·æ£æ¥å¿«ç§ï¼ä¾¿äºé¨ç½²åææ¥åºç¡ä¾èµç¶æã
def health_check() -> dict:
    snapshot = health_snapshot()
    log_event(logger, "health.check.completed", status=snapshot["status"])
    return snapshot
