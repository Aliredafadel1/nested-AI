"""
Test configuration.

Two problems solved here:

1. Sync DB cleanup (no asyncio.run()): the previous asyncio.run(_cleanup()) in
   pytest_configure created a temporary event loop that left stale global asyncio
   state, causing 'Future attached to a different loop' errors when anyio later
   created the TestClient's portal loop. We now use psycopg2 (sync) instead.

2. Persistent portal per test file: Starlette 0.37.x _portal_factory() creates a
   NEW anyio event loop per HTTP request unless self.portal is set (which only
   happens when TestClient is used as a context manager). A new loop per request
   means Redis/asyncpg connections from request N are associated with loop N-1
   (closed), causing fd-reuse + 'Future attached to a different loop' bugs.
   The autouse session fixture below calls __enter__() on every module-level
   TestClient BEFORE tests run, giving each one a stable, persistent portal.
"""
import os
import sys

# Force testing mode regardless of what the container's ENVIRONMENT var says.
# setdefault() was a no-op when the container already has ENVIRONMENT=development.
# This must run before any app imports so NullPool and fresh-Redis-client paths
# take effect.
os.environ["ENVIRONMENT"] = "testing"

import psycopg2
import pytest

# ── DB cleanup (synchronous, no asyncio.run()) ───────────────────────────────

def pytest_configure(config):
    _flush_redis_rate_keys()
    _cleanup_sync()


def _flush_redis_rate_keys():
    """Delete all rate:ip:* and rate:llm:* keys so leftover counts from prior
    runs can't trip the rate limiter or LLM daily limits during the current
    test session."""
    import redis as syncredis
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    try:
        r = syncredis.from_url(redis_url, decode_responses=True)
        for pattern in ("rate:ip:*", "rate:llm:*"):
            keys = r.keys(pattern)
            if keys:
                r.delete(*keys)
        r.close()
    except Exception as e:
        print(f"[conftest] Redis flush skipped — could not connect: {e}")


def _cleanup_sync():
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://nestai:nestai@db:5432/nestai",
    )
    dsn = url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = psycopg2.connect(dsn, connect_timeout=10)
    except Exception as e:
        print(f"[conftest] DB cleanup skipped — could not connect: {e}")
        return
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM roommate_requests WHERE from_user_id > 11 OR to_user_id > 11")
        cur.execute("DELETE FROM saved_listings WHERE user_id > 11")
        cur.execute("DELETE FROM agent_sessions WHERE user_id > 11")
        cur.execute("DELETE FROM student_memory WHERE user_id > 11")
        cur.execute("DELETE FROM cost_estimates WHERE user_id > 11 OR user_id = 0")
        cur.execute("DELETE FROM contracts WHERE user_id > 11")
        cur.execute("DELETE FROM notifications WHERE user_id > 11")
        cur.execute("DELETE FROM fraud_reports WHERE listing_id > 50")
        cur.execute("DELETE FROM listing_photos WHERE listing_id > 50")
        cur.execute("DELETE FROM listing_verifications WHERE listing_id > 50")
        cur.execute("DELETE FROM listings WHERE id > 50")
        cur.execute("DELETE FROM student_profiles WHERE user_id > 11")
        cur.execute("DELETE FROM landlord_profiles WHERE user_id > 11")
        cur.execute("DELETE FROM users WHERE id > 11")
        cur.execute(
            "SELECT setval('users_id_seq', "
            "GREATEST(100, (SELECT COALESCE(MAX(id), 100) FROM users)))"
        )
        cur.execute(
            "SELECT setval('listings_id_seq', "
            "GREATEST(100, (SELECT COALESCE(MAX(id), 100) FROM listings)))"
        )
        print("[conftest] DB cleanup complete.")
    except Exception as e:
        print(f"[conftest] DB cleanup error: {e}")
    finally:
        cur.close()
        conn.close()


# ── Persistent portal for all TestClient instances ───────────────────────────

@pytest.fixture(scope="session", autouse=True)
def persistent_test_clients():
    """Enter all module-level TestClient instances into context managers.

    TestClient._portal_factory() creates a new anyio event loop per request
    unless self.portal is set. Calling __enter__() sets self.portal to a
    persistent portal (one event loop for all requests in the same client),
    which prevents fd-reuse / cross-loop Future conflicts with Redis and asyncpg.
    """
    test_module_names = [
        "tests.test_api_listings",
        "tests.test_embeddings",
        "tests.test_agent_flow",
        "tests.test_fraud",
        "tests.test_contracts",
        "tests.test_agent_tools",
    ]
    clients = []
    for name in test_module_names:
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "client"):
            clients.append(mod.client)

    for c in clients:
        c.__enter__()

    yield

    for c in reversed(clients):
        try:
            c.__exit__(None, None, None)
        except Exception:
            pass
