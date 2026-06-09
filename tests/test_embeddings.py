"""Phase 2a integration tests — BGE-M3 embeddings and roommate matching.
Runs against real PostgreSQL + Redis. No mocks.

BGE-M3 unit tests are skipped unless the model cache is present (run in worker-low).
Celery-dependent tests inject fake 1024-dim vectors directly into the DB so they run
without needing a Celery worker — this tests the full API/SQL chain.
"""
import asyncio
import os

import asyncpg
import pytest
from starlette.testclient import TestClient

from app.main import app
from core.config import settings

client = TestClient(app, raise_server_exceptions=True)

# One shared fake 1024-dim vector for injection tests
FAKE_VECTOR = "[" + ",".join(["0.001"] * 1024) + "]"

# Orthogonal vector: first 512 dims high, last 512 near-zero — cosine sim ≈ 0 with FAKE_VECTOR_ORT
_half = 512
FAKE_VECTOR_OWL  = "[" + ",".join(["1.0"] * _half + ["0.0001"] * _half) + "]"
FAKE_VECTOR_BIRD = "[" + ",".join(["0.0001"] * _half + ["1.0"] * _half) + "]"


def _dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _register_login(email: str, role: str = "student") -> str:
    client.post("/auth/register", json={"email": email, "password": "Test1234!", "role": role})
    resp = client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 200, f"login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def _onboard(token: str, **kwargs) -> None:
    defaults = {
        "university_id": 1,
        "budget_min": 400, "budget_max": 700,
        "sleep_schedule": "night_owl",
        "study_habits": "quiet",
        "cleanliness": "high",
        "guests": "rarely",
        "language": "mixed",
    }
    defaults.update(kwargs)
    resp = client.post("/users/onboarding", json=defaults,
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"onboarding failed: {resp.text}"


def _inject_listing_embedding(listing_id: int) -> None:
    """Directly write a fake 1024-dim vector into listings.embedding."""
    async def _run():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                f"UPDATE listings SET embedding = '{FAKE_VECTOR}'::vector WHERE id = $1",
                listing_id
            )
        finally:
            await conn.close()
    asyncio.run(_run())


def _inject_profile_vectors(user_id: int, vector: str = FAKE_VECTOR) -> None:
    """Write fake 1024-dim vectors into all 6 student_profile embedding columns."""
    async def _run():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                f"""
                UPDATE student_profiles SET
                    embedding      = '{vector}'::vector,
                    dim_sleep      = '{vector}'::vector,
                    dim_study      = '{vector}'::vector,
                    dim_cleanliness= '{vector}'::vector,
                    dim_guests     = '{vector}'::vector,
                    dim_budget     = '{vector}'::vector
                WHERE user_id = $1
                """,
                user_id
            )
        finally:
            await conn.close()
    asyncio.run(_run())


def _get_user_id(email: str) -> int:
    async def _run():
        conn = await asyncpg.connect(_dsn())
        try:
            row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
            return row["id"]
        finally:
            await conn.close()
    return asyncio.run(_run())


# ── BGE-M3 unit tests (skipped unless model cache present) ───────────────────

@pytest.mark.skipif(
    not os.path.exists("/root/.cache/huggingface"),
    reason="BGE-M3 model cache not present — run in worker-low container",
)
def test_embed_text_dimension():
    """embed_text returns exactly 1024-dim vector."""
    from core.embeddings import _load_model, embed_text
    _load_model()
    vec = embed_text("test listing in Hamra Beirut")
    assert len(vec) == 1024


@pytest.mark.skipif(
    not os.path.exists("/root/.cache/huggingface"),
    reason="BGE-M3 model cache not present — run in worker-low container",
)
def test_embed_text_normalized():
    """Normalized vector has magnitude ≈ 1.0."""
    import math

    from core.embeddings import _load_model, embed_text
    _load_model()
    vec = embed_text("student looking for quiet studio near AUB")
    magnitude = math.sqrt(sum(v * v for v in vec))
    assert abs(magnitude - 1.0) < 1e-4


@pytest.mark.skipif(
    not os.path.exists("/root/.cache/huggingface"),
    reason="BGE-M3 model cache not present — run in worker-low container",
)
def test_embed_batch_efficiency():
    """embed_batch returns correct count and dimensions."""
    from core.embeddings import _load_model, embed_batch
    _load_model()
    texts = ["sleep schedule: night_owl", "study habits: quiet", "cleanliness: high"]
    vecs = embed_batch(texts)
    assert len(vecs) == 3
    for vec in vecs:
        assert len(vec) == 1024


# ── Listing embedding tests (vector injected directly) ───────────────────────

def test_listing_embedding_stored():
    """After creating a listing and injecting a vector, the listing is retrievable."""
    token = _register_login("embed_ll@test.com", "landlord")
    resp = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "Embed test listing Hamra", "price": 500, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    listing_id = resp.json()["id"]

    # Inject fake vector (simulates what worker-low would do)
    _inject_listing_embedding(listing_id)

    # Verify DB has the vector
    async def _check():
        conn = await asyncpg.connect(_dsn())
        try:
            row = await conn.fetchrow(
                "SELECT embedding IS NOT NULL AS has_embed FROM listings WHERE id = $1",
                listing_id
            )
            return row["has_embed"]
        finally:
            await conn.close()

    assert asyncio.run(_check()), "listing.embedding is NULL after injection"


# ── Profile embedding tests ───────────────────────────────────────────────────

def test_profile_all_6_vectors_populated():
    """After onboarding + vector injection, all 6 columns are non-null."""
    token = _register_login("embed_stu@test.com", "student")
    _onboard(token)
    user_id = _get_user_id("embed_stu@test.com")

    # Inject all 6 fake vectors (simulates what worker-low would do)
    _inject_profile_vectors(user_id)

    async def _check():
        conn = await asyncpg.connect(_dsn())
        try:
            row = await conn.fetchrow(
                """
                SELECT
                    embedding IS NOT NULL        AS e,
                    dim_sleep IS NOT NULL        AS ds,
                    dim_study IS NOT NULL        AS dst,
                    dim_cleanliness IS NOT NULL  AS dc,
                    dim_guests IS NOT NULL       AS dg,
                    dim_budget IS NOT NULL       AS db
                FROM student_profiles WHERE user_id = $1
                """,
                user_id
            )
            return dict(row)
        finally:
            await conn.close()

    columns = asyncio.run(_check())
    assert all(columns.values()), f"Not all 6 vectors populated: {columns}"


# ── Roommate matching tests ───────────────────────────────────────────────────

def test_no_embedding_returns_422():
    """Student without onboarding → GET /roommate/matches → 422."""
    token = _register_login("noembed@test.com")
    resp = client.get("/roommate/matches", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


def test_roommate_match_5_dimensions():
    """GET /roommate/matches → all 5 dimension keys present, values in [0, 1]."""
    token_a = _register_login("match_a@test.com")
    token_b = _register_login("match_b@test.com")
    _onboard(token_a, sleep_schedule="night_owl")
    _onboard(token_b, sleep_schedule="night_owl")

    uid_a = _get_user_id("match_a@test.com")
    uid_b = _get_user_id("match_b@test.com")

    # Inject same vector for both (they should be highly compatible)
    _inject_profile_vectors(uid_a, FAKE_VECTOR)
    _inject_profile_vectors(uid_b, FAKE_VECTOR)

    resp = client.get("/roommate/matches",
                      headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    matches = resp.json()
    assert len(matches) > 0, "Expected at least one match"

    m = matches[0]
    assert "score" in m and 0 <= m["score"] <= 1
    dims = m["dimensions"]
    for key in ("sleep", "study", "cleanliness", "guests", "budget"):
        assert key in dims, f"Missing dimension: {key}"
        assert 0 <= dims[key] <= 1, f"Dimension {key} out of range: {dims[key]}"


def test_opposite_sleep_low_score():
    """Night owl vs early bird → sleep dimension score < 0.4."""
    token_owl  = _register_login("owl@test.com")
    token_bird = _register_login("bird@test.com")
    _onboard(token_owl,  sleep_schedule="night_owl")
    _onboard(token_bird, sleep_schedule="early_bird")

    uid_owl  = _get_user_id("owl@test.com")
    uid_bird = _get_user_id("bird@test.com")

    # Inject orthogonal vectors: owl and bird have opposite half-space vectors
    # Cosine similarity between FAKE_VECTOR_OWL and FAKE_VECTOR_BIRD ≈ 0.0
    _inject_profile_vectors(uid_owl,  FAKE_VECTOR_OWL)
    _inject_profile_vectors(uid_bird, FAKE_VECTOR_BIRD)

    resp = client.get("/roommate/matches",
                      headers={"Authorization": f"Bearer {token_owl}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    matches = resp.json()

    bird_match = next((m for m in matches if m["user_id"] == uid_bird), None)
    assert bird_match is not None, "early_bird user not in matches"
    assert bird_match["dimensions"]["sleep"] < 0.4, (
        f"Expected sleep score < 0.4 for opposite vectors, got {bird_match['dimensions']['sleep']}"
    )


def test_send_roommate_request():
    """POST /roommate/requests → 201 with status pending."""
    token_a = _register_login("req_a@test.com")
    _register_login("req_b@test.com")
    b_id = _get_user_id("req_b@test.com")

    resp = client.post("/roommate/requests",
                       json={"to_user_id": b_id},
                       headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"
