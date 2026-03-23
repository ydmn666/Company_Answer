from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.core.logging_utils import get_log_file_path
from app.db.session import SessionLocal
from app.services.cache_service import _redis_client


def _component(status: str, detail: str | None = None, **extra) -> dict:
    payload = {"status": status}
    if detail is not None:
        payload["detail"] = detail
    payload.update(extra)
    return payload


def check_database() -> dict:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return _component("ok")
    except Exception as exc:
        return _component("error", detail=str(exc))
    finally:
        db.close()


def check_redis() -> dict:
    if not settings.redis_cache_enabled:
        return _component("disabled", detail="redis cache disabled")

    client = _redis_client()
    if client is None:
        return _component("error", detail="redis client unavailable")

    try:
        client.ping()
        return _component("ok")
    except Exception as exc:
        return _component("error", detail=str(exc))


def check_log_directory() -> dict:
    try:
        log_path = get_log_file_path()
        log_dir = log_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        probe = log_dir / ".healthcheck.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return _component("ok", path=str(log_dir))
    except Exception as exc:
        return _component("error", detail=str(exc))


def check_document_storage() -> dict:
    try:
        storage_dir = Path(settings.document_storage_dir)
        if not storage_dir.is_absolute():
            storage_dir = Path(__file__).resolve().parents[2] / storage_dir
        storage_dir.mkdir(parents=True, exist_ok=True)
        probe = storage_dir / ".healthcheck.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return _component("ok", path=str(storage_dir))
    except Exception as exc:
        return _component("error", detail=str(exc))


def health_snapshot() -> dict:
    components = {
        "database": check_database(),
        "redis": check_redis(),
        "log_dir": check_log_directory(),
        "document_storage": check_document_storage(),
    }
    overall_status = "ok"
    if any(item["status"] == "error" for item in components.values()):
        overall_status = "degraded"
    return {
        "status": overall_status,
        "app_env": settings.app_env,
        "components": components,
    }
