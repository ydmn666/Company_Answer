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


# 兼容旧库结构：如果 users 表没有 role 字段，就在启动时补齐。
def ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "role" not in user_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'employee'")
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    # V1 阶段直接建表，避免引入迁移工具增加理解成本。
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()

    # 写入演示数据，方便前端开箱即测。
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Enterprise Knowledge Retrieval API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 前端请求的 /api/* 都从这里挂出去。
app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    # Docker / 探活检查接口。
    return {"status": "ok"}
