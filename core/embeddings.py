"""BGE-M3 embedding service. Loaded once at Celery worker startup via worker_process_init signal."""
from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger(__name__)

_model = None  # SentenceTransformer instance, set by _load_model()

EMBED_DIM = 1024
EMBED_CACHE_TTL = 48 * 3600  # 48 hours


def _load_model() -> None:
    global _model
    if _model is not None:
        return
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("BAAI/bge-m3")
    logger.info("BGE-M3 model loaded")


try:
    from celery.signals import worker_process_init

    @worker_process_init.connect
    def _on_worker_init(**kwargs):
        _load_model()
except ImportError:
    pass


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _get_cached(text: str) -> list[float] | None:
    try:
        from core.redis import get_sync_redis, RedisKeys
        import json
        r = get_sync_redis()
        try:
            raw = r.get(RedisKeys.embed_cache(_cache_key(text)))
            return json.loads(raw) if raw else None
        finally:
            r.close()
    except Exception:
        return None


def _set_cached(text: str, vector: list[float]) -> None:
    try:
        from core.redis import get_sync_redis, RedisKeys
        import json
        r = get_sync_redis()
        try:
            r.setex(RedisKeys.embed_cache(_cache_key(text)), EMBED_CACHE_TTL, json.dumps(vector))
        finally:
            r.close()
    except Exception:
        pass


def embed_text(text: str, normalize: bool = True) -> list[float]:
    if _model is None:
        raise NotImplementedError("BGE-M3 not loaded. Worker not initialised.")

    cached = _get_cached(text)
    if cached is not None:
        return cached

    vec = _model.encode(text, normalize_embeddings=normalize).tolist()
    if len(vec) != EMBED_DIM:
        raise ValueError(f"Expected {EMBED_DIM}-dim vector, got {len(vec)}")

    _set_cached(text, vec)
    return vec


def embed_batch(texts: list[str], normalize: bool = True) -> list[list[float]]:
    if _model is None:
        raise NotImplementedError("BGE-M3 not loaded. Worker not initialised.")

    results: list[list[float] | None] = [_get_cached(t) for t in texts]
    uncached_idx = [i for i, r in enumerate(results) if r is None]

    if uncached_idx:
        uncached_texts = [texts[i] for i in uncached_idx]
        vecs = _model.encode(uncached_texts, normalize_embeddings=normalize).tolist()
        for i, vec in zip(uncached_idx, vecs):
            if len(vec) != EMBED_DIM:
                raise ValueError(f"Expected {EMBED_DIM}-dim vector, got {len(vec)}")
            _set_cached(texts[i], vec)
            results[i] = vec

    return results  # type: ignore[return-value]
