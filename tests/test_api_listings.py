"""Integration tests for Phase 1: auth flow, listings CRUD, ownership, photo upload, filters.
Runs against real PostgreSQL + Redis containers (no mocks).
Uses Starlette TestClient (sync) to avoid asyncio event-loop conflicts with asyncpg.
"""
import io

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_and_login(email: str, role: str) -> tuple[str, str]:
    client.post("/auth/register", json={"email": email, "password": "Test1234!", "role": role})
    resp = client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    refresh = resp.cookies.get("refresh_token")
    return token, refresh


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Auth flow ─────────────────────────────────────────────────────────────────

def test_register_student():
    resp = client.post("/auth/register", json={
        "email": "student1@test.com", "password": "Test1234!", "role": "student"
    })
    assert resp.status_code == 201
    assert "access_token" in resp.json()
    assert resp.cookies.get("refresh_token") is not None


def test_register_duplicate_email():
    data = {"email": "dup@test.com", "password": "Test1234!", "role": "student"}
    client.post("/auth/register", json=data)
    resp = client.post("/auth/register", json=data)
    assert resp.status_code == 400


def test_login_wrong_password():
    client.post("/auth/register", json={"email": "wp@test.com", "password": "Test1234!", "role": "student"})
    resp = client.post("/auth/login", json={"email": "wp@test.com", "password": "Wrong!"})
    assert resp.status_code == 401


def test_protected_endpoint_without_token():
    resp = client.get("/listings/saved")
    assert resp.status_code == 401


def test_logout_deletes_refresh():
    token, _ = register_and_login("logout@test.com", "student")
    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204


# ── Listings CRUD ─────────────────────────────────────────────────────────────

def test_get_listings_anonymous():
    resp = client.get("/listings")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_listing_as_landlord():
    token, _ = register_and_login("landlord1@test.com", "landlord")
    resp = client.post("/listings", json={
        "neighbourhood_id": 1,
        "title": "Test listing",
        "price": 500,
        "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["title"] == "Test listing"
    assert resp.json()["status"] == "active"


def test_create_listing_as_student_forbidden():
    token, _ = register_and_login("student2@test.com", "student")
    resp = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "x", "price": 400, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_update_own_listing():
    token, _ = register_and_login("landlord2@test.com", "landlord")
    create = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "Old title", "price": 500, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    listing_id = create.json()["id"]
    resp = client.put(f"/listings/{listing_id}", json={"title": "New title"},
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"


def test_update_other_landlord_listing_forbidden():
    token1, _ = register_and_login("landlord3@test.com", "landlord")
    token2, _ = register_and_login("landlord4@test.com", "landlord")
    create = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "Mine", "price": 500, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token1}"})
    listing_id = create.json()["id"]
    resp = client.put(f"/listings/{listing_id}", json={"title": "Stolen"},
                      headers={"Authorization": f"Bearer {token2}"})
    assert resp.status_code == 403


def test_soft_delete_listing():
    token, _ = register_and_login("landlord5@test.com", "landlord")
    create = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "To delete", "price": 500, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    listing_id = create.json()["id"]

    resp = client.delete(f"/listings/{listing_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    get_resp = client.get("/listings")
    ids = [item["id"] for item in get_resp.json()]
    assert listing_id not in ids


# ── Photo upload ──────────────────────────────────────────────────────────────

def test_upload_valid_jpeg():
    token, _ = register_and_login("photo_landlord@test.com", "landlord")
    create = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "Photo test", "price": 500, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    listing_id = create.json()["id"]

    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    resp = client.post(
        f"/listings/{listing_id}/photos",
        files={"file": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert "url" in resp.json()


def test_upload_invalid_magic_bytes():
    token, _ = register_and_login("magic_landlord@test.com", "landlord")
    create = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "Magic test", "price": 500, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    listing_id = create.json()["id"]

    fake_bytes = b"NOTAJPEG" + b"\x00" * 100
    resp = client.post(
        f"/listings/{listing_id}/photos",
        files={"file": ("fake.jpg", io.BytesIO(fake_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ── Filters ───────────────────────────────────────────────────────────────────

def test_filter_by_max_price():
    resp = client.get("/listings?max_price=400")
    assert resp.status_code == 200
    for listing in resp.json():
        assert listing["price"] <= 400


def test_filter_by_neighbourhood_id():
    resp = client.get("/listings?neighbourhood_id=1")
    assert resp.status_code == 200
    for listing in resp.json():
        assert listing["neighbourhood_id"] == 1


# ── Save / unsave ─────────────────────────────────────────────────────────────

def test_save_and_retrieve_listing():
    s_token, _ = register_and_login("saver@test.com", "student")
    ll_token, _ = register_and_login("saver_landlord@test.com", "landlord")
    create = client.post("/listings", json={
        "neighbourhood_id": 1, "title": "Save me", "price": 500, "bedrooms": 1,
    }, headers={"Authorization": f"Bearer {ll_token}"})
    listing_id = create.json()["id"]

    save = client.post(f"/listings/{listing_id}/save",
                       headers={"Authorization": f"Bearer {s_token}"})
    assert save.status_code == 204

    saved = client.get("/listings/saved", headers={"Authorization": f"Bearer {s_token}"})
    assert saved.status_code == 200
    ids = [item["id"] for item in saved.json()]
    assert listing_id in ids


# ── Onboarding ────────────────────────────────────────────────────────────────

def test_student_onboarding():
    token, _ = register_and_login("onboard@test.com", "student")
    resp = client.post("/users/onboarding", json={
        "university_id": 1,
        "budget_min": 400,
        "budget_max": 700,
        "sleep_schedule": "night_owl",
        "study_habits": "quiet",
        "cleanliness": "high",
        "guests": "rarely",
        "language": "mixed",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["sleep_schedule"] == "night_owl"


def test_landlord_cannot_onboard():
    token, _ = register_and_login("ll_onboard@test.com", "landlord")
    resp = client.post("/users/onboarding", json={"budget_min": 400},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
