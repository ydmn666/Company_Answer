import hashlib
import json
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.services.retrieval_service import normalize_question


# æ ¹æ®å½åéç½®è¿å Redis å®¢æ·ç«¯ï¼ä¸å¯ç¨æ¶è¿å Noneã
def _redis_client():
    if not settings.redis_cache_enabled:
        return None

    try:
        import redis

        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


# ä¸ºå½åç¥è¯åºçæç®åæçº¹ï¼ç¨äºå¤æ­ç¼å­æ¯å¦å¤±æã
def knowledge_base_fingerprint(db: Session) -> str:
    document_count, updated_at = db.query(func.count(Document.id), func.max(Document.updated_at)).one()
    latest = updated_at.isoformat() if updated_at else "none"
    raw = f"{document_count}:{latest}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# æé é®ç­ç¼å­ keyï¼åºåé®é¢ãæ¨¡åæä¾æ¹åç¥è¯åºçæ¬ã
def build_answer_cache_key(question: str, provider: str | None, kb_fingerprint: str) -> str:
    normalized = normalize_question(question)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    provider_name = (provider or settings.llm_default_provider or "local").lower()
    return f"qa:{kb_fingerprint}:{provider_name}:{digest}"


# æé®é¢åç¥è¯åºçæ¬è¯»åç¼å­ç­æ¡ã
def get_cached_answer(question: str, provider: str | None, kb_fingerprint: str) -> dict | None:
    client = _redis_client()
    if client is None:
        return None

    key = build_answer_cache_key(question, provider, kb_fingerprint)
    try:
        value = client.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


# å°é®ç­ç»æåå¥ Redis ç¼å­å¹¶è®¾ç½®è¿ææ¶é´ã
def set_cached_answer(
    question: str,
    provider: str | None,
    kb_fingerprint: str,
    payload: dict,
) -> None:
    client = _redis_client()
    if client is None:
        return

    key = build_answer_cache_key(question, provider, kb_fingerprint)
    body = {
        **payload,
        "cached_at": datetime.utcnow().isoformat(),
    }
    try:
        client.setex(key, settings.redis_cache_ttl_seconds, json.dumps(body, ensure_ascii=False))
    except Exception:
        return
