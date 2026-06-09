import os
from collections.abc import AsyncGenerator

import redis as syncredis
import redis.asyncio as aioredis

from core.config import settings

_TESTING = os.environ.get("ENVIRONMENT") == "testing"

# ── Shared connection pool (production) ──────────────────────────────────────
# In testing we skip the shared pool entirely: each request gets a fresh client
# so connections never bind to a stale event loop (same fix as NullPool for PG).
_pool: aioredis.ConnectionPool | None = None if _TESTING else aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


def get_async_redis() -> aioredis.Redis:
    """Return an async Redis client. In testing, a fresh client per call."""
    if _TESTING:
        return aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return aioredis.Redis(connection_pool=_pool)


async def get_redis_dep() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency. In testing, yields a fresh client and closes it."""
    if _TESTING:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            yield client
        finally:
            await client.aclose()
    else:
        yield aioredis.Redis(connection_pool=_pool)


def get_sync_redis() -> syncredis.Redis:
    return syncredis.from_url(settings.REDIS_URL, decode_responses=True)


def get_pubsub_redis() -> aioredis.Redis:
    # Pub/sub needs its own dedicated connection, not the shared pool.
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ── Key patterns ─────────────────────────────────────────────────────────────

class RedisKeys:
    """Single source of truth for all 16 Redis key patterns."""

    @staticmethod
    def session(user_id: int, session_id: str) -> str:
        return f"session:{user_id}:{session_id}"

    @staticmethod
    def refresh(user_id: int) -> str:
        return f"refresh:{user_id}"

    @staticmethod
    def rate_ip(ip: str, endpoint: str) -> str:
        return f"rate:ip:{ip}:{endpoint}"

    @staticmethod
    def rate_llm(user_id: int, task: str) -> str:
        return f"rate:llm:{user_id}:{task}"

    @staticmethod
    def llm_cache(task: str, prompt_hash: str) -> str:
        return f"llm:{task}:{prompt_hash}"

    @staticmethod
    def embed_cache(text_hash: str) -> str:
        return f"embed:{text_hash}"

    @staticmethod
    def sse_channel(user_id: int) -> str:
        return f"sse:{user_id}"

    @staticmethod
    def embed_lock(listing_id: int) -> str:
        return f"lock:embed:{listing_id}"

    @staticmethod
    def fraud_cache(listing_id: int) -> str:
        return f"fraud:{listing_id}"

    @staticmethod
    def area_cache(neighborhood_id: int) -> str:
        return f"area:{neighborhood_id}"

    @staticmethod
    def commute_cache(listing_id: int, university_id: int) -> str:
        return f"commute:{listing_id}:{university_id}"

    @staticmethod
    def contract_status(contract_id: int) -> str:
        return f"contract:{contract_id}:status"

    @staticmethod
    def agent_session(user_id: int, session_id: str) -> str:
        return f"session:{user_id}:{session_id}"

    @staticmethod
    def llm_rate_daily(user_id: int, task: str) -> str:
        return f"rate:llm:{user_id}:{task}"

    @staticmethod
    def sftp_lock() -> str:
        return "lock:sftp:watcher"

    @staticmethod
    def notification_unread(user_id: int) -> str:
        return f"notif:unread:{user_id}"
