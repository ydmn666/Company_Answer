import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import settings


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if getattr(record, "event", None):
            payload["event"] = record.event
        if getattr(record, "extra_data", None):
            payload.update(record.extra_data)
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        if user_id:
            payload["user_id"] = user_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _log_path() -> Path:
    base = Path(settings.log_dir)
    if not base.is_absolute():
        base = Path(__file__).resolve().parents[2] / base
    base.mkdir(parents=True, exist_ok=True)
    return base / "app.log"


def get_log_file_path() -> Path:
    return _log_path()


def configure_logging() -> None:
    root = logging.getLogger()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)
    root.handlers.clear()

    formatter: logging.Formatter
    if settings.log_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    if settings.log_to_file:
        file_handler = RotatingFileHandler(
            _log_path(),
            maxBytes=settings.log_file_max_bytes,
            backupCount=settings.log_file_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def set_request_context(request_id: str | None = None, user_id: str | None = None) -> None:
    request_id_var.set(request_id)
    user_id_var.set(user_id)


def clear_request_context() -> None:
    request_id_var.set(None)
    user_id_var.set(None)


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **payload: Any) -> None:
    logger.log(level, event, extra={"event": event, "extra_data": payload})
