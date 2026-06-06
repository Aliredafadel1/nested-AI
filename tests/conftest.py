"""
Test configuration: removes only test-created data before the session.
Preserves seed data: users/listings with id ≤ seed range.
Dependent tables are deleted in FK-safe order (children before parents).
"""
import os

# Must be set before database.py is imported so NullPool is used (avoids
# asyncpg "another operation in progress" errors when asyncio.run() is called
# in pytest_configure and the TestClient creates a second event loop).
os.environ.setdefault("ENVIRONMENT", "testing")

import asyncio
import asyncpg
import pytest


def pytest_configure(config):
    asyncio.run(_cleanup())


async def _cleanup():
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://nestai:nestai@docker-db-1:5432/nestai",
    )
    dsn = url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(dsn, timeout=10)
    except Exception as e:
        print(f"[conftest] DB cleanup skipped — could not connect: {e}")
        return
    try:
        # Delete child tables FIRST (FK-safe order)
        await conn.execute("DELETE FROM roommate_requests WHERE from_user_id > 11 OR to_user_id > 11")
        await conn.execute("DELETE FROM saved_listings WHERE user_id > 11")
        await conn.execute("DELETE FROM agent_sessions WHERE user_id > 11")
        await conn.execute("DELETE FROM student_memory WHERE user_id > 11")
        await conn.execute("DELETE FROM cost_estimates WHERE user_id > 11 OR user_id = 0")
        await conn.execute("DELETE FROM contracts WHERE user_id > 11")
        await conn.execute("DELETE FROM notifications WHERE user_id > 11")
        # Listing children before listings
        await conn.execute("DELETE FROM fraud_reports WHERE listing_id > 50")
        await conn.execute("DELETE FROM listing_photos WHERE listing_id > 50")
        await conn.execute("DELETE FROM listing_verifications WHERE listing_id > 50")
        await conn.execute("DELETE FROM listings WHERE id > 50")
        # Profiles before users
        await conn.execute("DELETE FROM student_profiles WHERE user_id > 11")
        await conn.execute("DELETE FROM landlord_profiles WHERE user_id > 11")
        # Users last
        await conn.execute("DELETE FROM users WHERE id > 11")
        # Reset sequences above seed range
        await conn.execute(
            "SELECT setval('users_id_seq', "
            "GREATEST(100, (SELECT COALESCE(MAX(id), 100) FROM users)))"
        )
        await conn.execute(
            "SELECT setval('listings_id_seq', "
            "GREATEST(100, (SELECT COALESCE(MAX(id), 100) FROM listings)))"
        )
        print("[conftest] DB cleanup complete.")
    except Exception as e:
        print(f"[conftest] DB cleanup error: {e}")
    finally:
        await conn.close()
