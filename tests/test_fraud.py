"""Integration tests for Phase 2b: fraud detection + area intelligence.
Runs against real PostgreSQL + Redis (no mocks). Uses sync TestClient.
"""
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def register_and_login_landlord(email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "Test9999!", "role": "landlord"})
    resp = client.post("/auth/login", json={"email": email, "password": "Test9999!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def create_listing(token: str, price: int = 600) -> int:
    resp = client.post("/listings", json={
        "neighbourhood_id": 1,
        "title": "Test listing for fraud",
        "price": price,
        "bedrooms": 2,
        "description": "A test listing for fraud detection.",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, f"create listing failed: {resp.text}"
    return resp.json()["id"]


# ── Test 1: GET /fraud/{id} returns valid schema ──────────────────────────────

def test_fraud_report_schema():
    token = register_and_login_landlord("fraud_t1@test.com")
    listing_id = create_listing(token)
    resp = client.get(f"/fraud/{listing_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "listing_id" in data
    assert "score" in data
    assert "evidence" in data
    for key in ["price_flags", "phone_flags", "photo_flags", "text_flags"]:
        assert key in data["evidence"]


# ── Test 2: Fraud report returns placeholder for new listing ──────────────────

def test_fraud_report_new_listing_has_score():
    token = register_and_login_landlord("fraud_t2@test.com")
    listing_id = create_listing(token)
    resp = client.get(f"/fraud/{listing_id}")
    assert resp.status_code == 200
    assert "score" in resp.json()
    assert isinstance(resp.json()["score"], (int, float))


# ── Test 3: Non-existent listing returns score placeholder ────────────────────

def test_fraud_report_nonexistent_listing():
    resp = client.get("/fraud/99999999")
    assert resp.status_code in (200, 404)


# ── Test 4: Area intelligence GET /areas/{name} ───────────────────────────────

def test_area_scores_hamra():
    resp = client.get("/areas/Hamra")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Hamra"
    assert data["electricity_hours"] is not None
    assert data["generator_cost"] is not None
    for key in ["internet", "transport", "safety", "student_vibe"]:
        assert key in data


def test_area_scores_achrafieh():
    resp = client.get("/areas/Achrafieh")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Achrafieh"


def test_area_scores_not_found():
    resp = client.get("/areas/nonexistent_area_xyz")
    assert resp.status_code == 404


# ── Test 5: Areas compare returns both neighbourhoods ─────────────────────────

def test_areas_compare():
    resp = client.post("/areas/compare", json={"area_a": "Hamra", "area_b": "Achrafieh"})
    assert resp.status_code == 200
    data = resp.json()
    assert "area_a" in data and "area_b" in data
    assert data["area_a"]["name"] == "Hamra"
    assert data["area_b"]["name"] == "Achrafieh"


def test_areas_compare_missing_area():
    resp = client.post("/areas/compare", json={"area_a": "Hamra", "area_b": "NonExistentXYZ"})
    assert resp.status_code == 404


# ── Test 6: Notifications list requires auth ──────────────────────────────────

def test_notifications_requires_auth():
    resp = client.get("/notifications")
    assert resp.status_code == 401


def test_notifications_empty_for_new_user():
    client.post("/auth/register", json={"email": "notif_test@test.com", "password": "Test9999!", "role": "student"})
    login = client.post("/auth/login", json={"email": "notif_test@test.com", "password": "Test9999!"})
    token = login.json()["access_token"]
    resp = client.get("/notifications", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── Test 7: Estimator requires auth ──────────────────────────────────────────

def test_estimator_requires_auth():
    resp = client.post("/estimator/calculate", json={"rent": 500, "neighbourhood_id": 1})
    assert resp.status_code == 401


def test_estimator_returns_breakdown():
    client.post("/auth/register", json={"email": "estimator_t@test.com", "password": "Test9999!", "role": "student"})
    login = client.post("/auth/login", json={"email": "estimator_t@test.com", "password": "Test9999!"})
    token = login.json()["access_token"]

    resp = client.post(
        "/estimator/calculate",
        json={"rent": 600, "neighbourhood_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for field in ["rent", "generator", "water", "internet", "transport", "total_monthly"]:
        assert field in data
    assert data["rent"] == 600
    assert data["total_monthly"] > 600  # always > rent
