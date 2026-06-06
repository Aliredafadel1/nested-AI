from typing import AsyncGenerator

import redis.asyncio as aioredis
import redis as syncredis
from core.config import settings


# ── Clients ──────────────────────────────────────────────────────────────────

def get_async_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis_dep() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency that opens and properly closes a Redis connection."""
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()


def get_sync_redis() -> syncredis.Redis:
    return syncredis.from_url(settings.REDIS_URL, decode_responses=True)


def get_pubsub_redis() -> aioredis.Redis:
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
