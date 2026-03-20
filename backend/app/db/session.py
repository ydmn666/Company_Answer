from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# engine 负责和 PostgreSQL 建立底层连接。
engine = create_engine(settings.database_url, future=True)

# SessionLocal 是每次请求操作数据库的会话工厂。
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    # FastAPI 依赖注入入口。
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
