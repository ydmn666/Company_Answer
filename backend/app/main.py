from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import chat_message, chat_session, document, document_chunk, user  # noqa: F401
from app.services.bootstrap_service import seed_demo_data


def _ensure_column(inspector, table_name: str, column_name: str, definition: str) -> None:
    if not inspector.has_table(table_name):
        return

    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        return

    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


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
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()

    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    yield


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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
