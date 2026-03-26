import math
import logging
import re
import time
from collections import Counter
from functools import lru_cache

from rank_bm25 import BM25Okapi
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.logging_utils import log_event
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")
LOCAL_EMBEDDING_DIM = max(settings.retrieval_embedding_fallback_dim, 8)
KEYWORD_PREFILTER_LIMIT = 160
KEYWORD_TERM_LIMIT = 8
logger = logging.getLogger(__name__)


# ç»ä¸è¾åºæ£ç´¢é¾è·¯çç»æåæ¥å¿ã
def _trace(event: str, **payload) -> None:
    log_event(logger, event, **payload)


# å°ä¸­è±æé®é¢åæç»ä¸çæ£ç´¢ tokenã
def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "")]


# å½ä¸åç¨æ·é®é¢ææ¬ï¼ä¾¿äºç¼å­ key åæ¯è¾ã
def normalize_question(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    return normalized


# æ©å±å³é®è¯ç²åº¦ï¼å¢å¼ºä¸­ææ£ç´¢å¬åè½åã
def expand_terms(text: str) -> set[str]:
    terms = set(tokenize(text))
    expanded = set(terms)
    for term in terms:
        if re.fullmatch(r"[\u4e00-\u9fff]+", term) and len(term) >= 2:
            max_size = min(4, len(term))
            for size in range(2, max_size + 1):
                for index in range(0, len(term) - size + 1):
                    expanded.add(term[index:index + size])
    return expanded


# è®¡ç®ä¸¤ä¸ªåéä¹é´çä½å¼¦ç¸ä¼¼åº¦ã
def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if left is None or right is None:
        return 0.0
    if len(left) == 0 or len(right) == 0 or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return numerator / (left_norm * right_norm)


# å¨æ¬å°æ¨¡åä¸å¯ç¨æ¶çæä¸ä¸ªè½»éåå¸åéä½ä¸ºååº embeddingã
def _local_hash_embedding(text: str) -> list[float]:
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * LOCAL_EMBEDDING_DIM

    counter = Counter(tokens)
    vector = [0.0] * LOCAL_EMBEDDING_DIM
    for token, count in counter.items():
        vector[hash(token) % LOCAL_EMBEDDING_DIM] += float(count)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            for size in range(2, min(4, len(token)) + 1):
                for index in range(0, len(token) - size + 1):
                    vector[hash(token[index:index + size]) % LOCAL_EMBEDDING_DIM] += 0.35

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


@lru_cache(maxsize=1)
# æå è½½æ¬å° embedding æ¨¡åã
def _load_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        _trace("load_sentence_transformer.start", model=settings.retrieval_embedding_model)
        return SentenceTransformer(settings.retrieval_embedding_model)
    except Exception:
        _trace("load_sentence_transformer.fallback_local", model=settings.retrieval_embedding_model)
        return None


@lru_cache(maxsize=1)
# æå è½½ reranker æ¨¡åã
def _load_cross_encoder():
    if not settings.retrieval_reranker_enabled:
        return None

    try:
        from sentence_transformers import CrossEncoder

        _trace("load_cross_encoder.start", model=settings.retrieval_reranker_model)
        return CrossEncoder(settings.retrieval_reranker_model)
    except Exception:
        _trace("load_cross_encoder.disabled", model=settings.retrieval_reranker_model)
        return None


# è¿åå½åå®éçæç embedding æ¨¡ååç§°ã
def current_embedding_model_name() -> str:
    if settings.retrieval_embedding_backend == "sentence_transformers" and _load_sentence_transformer():
        return settings.retrieval_embedding_model
    return "local-hash"


# ä¸ºé®é¢æåçææ¬çæåéè¡¨ç¤ºã
def generate_embedding(text: str) -> list[float]:
    started = time.perf_counter()
    if settings.retrieval_embedding_backend == "sentence_transformers":
        model = _load_sentence_transformer()
        if model is not None:
            try:
                vector = model.encode(text or "", normalize_embeddings=True)
                _trace(
                    "generate_embedding.remote_done",
                    backend=settings.retrieval_embedding_backend,
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                    text_len=len(text or ""),
                )
                return [float(value) for value in vector.tolist()]
            except Exception:
                pass

    _trace(
        "generate_embedding.local_done",
        backend="local-hash",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        text_len=len(text or ""),
    )
    return _local_hash_embedding(text)


# ç¨å³é®è¯é¢ç­å BM25 å¬ååéåçã
def _keyword_candidates(db: Session, question: str, limit: int) -> list[DocumentChunk]:
    started = time.perf_counter()
    terms = list(expand_terms(question))[:KEYWORD_TERM_LIMIT]
    if not terms:
        _trace("keyword_candidates.skip_no_terms", elapsed_ms=round((time.perf_counter() - started) * 1000, 2))
        return []

    conditions = []
    for term in terms:
        like_term = f"%{term}%"
        conditions.extend(
            [
                DocumentChunk.content.ilike(like_term),
                DocumentChunk.section_title.ilike(like_term),
                Document.title.ilike(like_term),
            ]
        )

    chunks = (
        db.query(DocumentChunk)
        .join(DocumentChunk.document)
        .options(joinedload(DocumentChunk.document))
        .filter(or_(*conditions))
        .limit(max(limit * 20, KEYWORD_PREFILTER_LIMIT))
        .all()
    )
    if not chunks:
        _trace("keyword_candidates.no_chunks", elapsed_ms=round((time.perf_counter() - started) * 1000, 2))
        return []

    corpus = [
        tokenize(f"{chunk.document.title if chunk.document else ''} {chunk.section_title or ''} {chunk.content}")
        for chunk in chunks
    ]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(question))
    ranked = sorted(zip(scores, chunks), key=lambda item: item[0], reverse=True)
    result = [chunk for score, chunk in ranked[:limit] if score > 0]
    _trace(
        "keyword_candidates.done",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        terms=len(terms),
        raw_chunks=len(chunks),
        result=len(result),
    )
    return result


# ç¨åéç¸ä¼¼åº¦å¬ååéåçã
def _vector_candidates(db: Session, query_embedding: list[float], limit: int) -> list[DocumentChunk]:
    started = time.perf_counter()
    model_name = current_embedding_model_name()
    try:
        result = (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.embedding.is_not(None), DocumentChunk.embedding_model == model_name)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
            .all()
        )
        _trace(
            "vector_candidates.db_done",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            model=model_name,
            result=len(result),
        )
        return result
    except Exception:
        chunks = (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.embedding.is_not(None), DocumentChunk.embedding_model == model_name)
            .all()
        )
        ranked = sorted(
            ((cosine_similarity(chunk.embedding, query_embedding), chunk) for chunk in chunks),
            key=lambda item: item[0],
            reverse=True,
        )
        result = [chunk for score, chunk in ranked[:limit] if score > 0]
        _trace(
            "vector_candidates.python_fallback_done",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            model=model_name,
            raw_chunks=len(chunks),
            result=len(result),
        )
        return result


# ä¸ºå·²å½ä¸­çåçè¡¥åååé»æ¥çæ®µï¼å¢å¼ºä¸ä¸æè¿ç»­æ§ã
def _expand_neighbors(
    db: Session,
    selected_chunks: list[DocumentChunk],
    by_id: dict[str, DocumentChunk],
) -> list[DocumentChunk]:
    started = time.perf_counter()
    expanded: dict[str, DocumentChunk] = {}
    missing_ids: set[str] = set()
    for chunk in selected_chunks:
        expanded[chunk.id] = chunk
        for _ in range(settings.retrieval_neighbor_window):
            if chunk.prev_chunk_id:
                missing_ids.add(chunk.prev_chunk_id)
            if chunk.next_chunk_id:
                missing_ids.add(chunk.next_chunk_id)

    unresolved_ids = [item for item in missing_ids if item not in by_id]
    if unresolved_ids:
        for chunk in (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.id.in_(unresolved_ids))
            .all()
        ):
            by_id[chunk.id] = chunk

    for chunk_id in missing_ids:
        if chunk_id in by_id:
            expanded[chunk_id] = by_id[chunk_id]
    result = list(expanded.values())
    _trace(
        "expand_neighbors.done",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        selected=len(selected_chunks),
        result=len(result),
    )
    return result


# å¯¹å¬åç»æåéæï¼æåæç»éå¥åç­é¶æ®µççæ®µè´¨éã
def rerank_chunks(question: str, query_embedding: list[float], chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    started = time.perf_counter()
    if not chunks:
        _trace("rerank.skip_empty", elapsed_ms=round((time.perf_counter() - started) * 1000, 2))
        return []

    encoder = _load_cross_encoder()
    if encoder is None:
        question_terms = expand_terms(question)
        ranked = []
        for chunk in chunks:
            haystack = f"{chunk.document.title if chunk.document else ''} {chunk.section_title or ''} {chunk.content}"
            lexical_score = len(question_terms & expand_terms(haystack))
            semantic_score = cosine_similarity(chunk.embedding, query_embedding)
            ranked.append((lexical_score + semantic_score, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        result = [chunk for _, chunk in ranked]
        _trace(
            "rerank.local_done",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            input=len(chunks),
            result=len(result),
        )
        return result

    try:
        pairs = [
            [
                question,
                f"{chunk.document.title if chunk.document else ''}\n{chunk.section_title or ''}\n{chunk.content}",
            ]
            for chunk in chunks[: settings.retrieval_reranker_top_k]
        ]
        scores = encoder.predict(pairs)
        reranked_head = [chunk for _, chunk in sorted(zip(scores, chunks[: settings.retrieval_reranker_top_k]), key=lambda item: float(item[0]), reverse=True)]
        result = reranked_head + chunks[settings.retrieval_reranker_top_k :]
        _trace(
            "rerank.encoder_done",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            input=len(chunks),
            result=len(result),
        )
        return result
    except Exception:
        _trace("rerank.exception_fallback", elapsed_ms=round((time.perf_counter() - started) * 1000, 2))
        return chunks


# æ§è¡å®æ´æ··åæ£ç´¢æµç¨å¹¶è¿åæç»å¼ç¨çæ®µã
def retrieve_top_chunks(db: Session, question: str, top_k: int | None = None) -> list[dict]:
    started = time.perf_counter()
    _trace("retrieve_top_chunks.start", question_len=len(question or ""))
    final_top_k = top_k or settings.retrieval_final_top_k
    query_embedding = generate_embedding(question)

    candidates: dict[str, DocumentChunk] = {}
    for chunk in _vector_candidates(db, query_embedding, settings.retrieval_semantic_top_k):
        candidates[chunk.id] = chunk
    for chunk in _keyword_candidates(db, question, settings.retrieval_keyword_top_k):
        candidates[chunk.id] = chunk

    all_chunk_map = {chunk.id: chunk for chunk in candidates.values()}
    expanded = _expand_neighbors(db, list(candidates.values()), all_chunk_map)
    for chunk in expanded:
        candidates[chunk.id] = chunk

    reranked = rerank_chunks(question, query_embedding, list(candidates.values()))
    top_chunks = reranked[:final_top_k]
    result = [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document.id,
            "document_title": chunk.document.title,
            "snippet": chunk.content[:320],
            "page_no": chunk.page_no,
            "section_title": chunk.section_title,
            "chunk_index": chunk.chunk_index,
        }
        for chunk in top_chunks
    ]
    _trace(
        "retrieve_top_chunks.done",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        candidates=len(candidates),
        top_chunks=len(result),
    )
    return result
