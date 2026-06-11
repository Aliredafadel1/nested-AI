"""BGE-M3 embedding service. Loaded once at Celery worker startup via worker_process_init signal."""
from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger(__name__)

_model = None  # SentenceTransformer instance, set by _load_model()
_load_attempted = False  # prevent repeated load attempts when model is unavailable

EMBED_DIM = 384
EMBED_CACHE_TTL = 48 * 3600  # 48 hours


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _load_model() -> None:
    global _model, _load_attempted
    if _model is not None or _load_attempted:
        return
    _load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded: %s", MODEL_NAME)
    except (ImportError, Exception) as exc:
        logger.warning("Embedding model unavailable (%s) — semantic search will use random fallback vectors", exc)
        _model = None


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
        import json

        from core.redis import RedisKeys, get_sync_redis
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
        import json

        from core.redis import RedisKeys, get_sync_redis
        r = get_sync_redis()
        try:
            r.setex(RedisKeys.embed_cache(_cache_key(text)), EMBED_CACHE_TTL, json.dumps(vector))
        finally:
            r.close()
    except Exception:
        pass


def _random_fallback_vector() -> list[float]:
    """Return a normalized random 1024-dim vector when BGE-M3 is unavailable."""
    import math
    import random
    vec = [random.gauss(0, 1) for _ in range(EMBED_DIM)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def embed_text(text: str, normalize: bool = True) -> list[float]:
    global _model
    if _model is None and not _load_attempted:
        logger.warning("BGE-M3 not pre-loaded — loading now (lazy fallback)")
        _load_model()

    cached = _get_cached(text)
    if cached is not None:
        return cached

    if _model is None:
        logger.warning("BGE-M3 unavailable — returning random fallback vector for query")
        return _random_fallback_vector()

    vec = _model.encode(text, normalize_embeddings=normalize).tolist()
    if len(vec) != EMBED_DIM:
        raise ValueError(f"Expected {EMBED_DIM}-dim vector, got {len(vec)}")

    _set_cached(text, vec)
    return vec


def embed_batch(texts: list[str], normalize: bool = True) -> list[list[float]]:
    global _model
    if _model is None and not _load_attempted:
        logger.warning("BGE-M3 not pre-loaded — loading now (lazy fallback)")
        _load_model()

    if _model is None:
        logger.warning("BGE-M3 unavailable — returning random fallback vectors for batch")
        return [_random_fallback_vector() for _ in texts]

    results: list[list[float] | None] = [_get_cached(t) for t in texts]
    uncached_idx = [i for i, r in enumerate(results) if r is None]

    if uncached_idx:
        uncached_texts = [texts[i] for i in uncached_idx]
        vecs = _model.encode(uncached_texts, normalize_embeddings=normalize).tolist()
        for i, vec in zip(uncached_idx, vecs, strict=True):
            if len(vec) != EMBED_DIM:
                raise ValueError(f"Expected {EMBED_DIM}-dim vector, got {len(vec)}")
            _set_cached(texts[i], vec)
            results[i] = vec

    return results  # type: ignore[return-value]
