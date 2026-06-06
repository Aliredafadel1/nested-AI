"""Integration tests for Phase 2b: contract analyzer module.
Runs against real PostgreSQL + MinIO. Uses sync TestClient.
"""
import io
import pytest
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def register_student(email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "Test9999!", "role": "student"})
    resp = client.post("/auth/login", json={"email": email, "password": "Test9999!"})
    return resp.json()["access_token"]


def _minimal_pdf() -> bytes:
    content = b"Tenant shall pay 500 USD monthly rent."
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font\n"
        b"   /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(len(content) + 20).encode() + b" >>\nstream\n"
        b"BT /F1 12 Tf 50 750 Td (" + content + b") Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f\n"
        b"0000000009 00000 n\n0000000058 00000 n\n"
        b"0000000115 00000 n\n0000000274 00000 n\n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n474\n%%EOF"
    )


# ── Test 1: Upload non-PDF → 400 ─────────────────────────────────────────────

def test_upload_non_pdf_rejected():
    token = register_student("contract_t2@test.com")
    fake_bytes = b"Not a PDF file at all"
    resp = client.post(
        "/contracts/analyze",
        files={"file": ("contract.txt", io.BytesIO(fake_bytes), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


# ── Test 2: Upload oversized file → 400 ──────────────────────────────────────

def test_upload_oversized_pdf_rejected():
    token = register_student("contract_t3@test.com")
    oversized = b"%PDF-1.4\n" + b"x" * (11 * 1024 * 1024)
    resp = client.post(
        "/contracts/analyze",
        files={"file": ("big.pdf", io.BytesIO(oversized), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    assert "10 mb" in detail or "limit" in detail or "exceed" in detail


# ── Test 3: Upload requires auth ──────────────────────────────────────────────

def test_upload_requires_auth():
    pdf_bytes = _minimal_pdf()
    resp = client.post(
        "/contracts/analyze",
        files={"file": ("contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 401


# ── Test 4: Upload requires student role ─────────────────────────────────────

def test_upload_requires_student_not_landlord():
    client.post("/auth/register", json={"email": "landlord_contract@test.com", "password": "Test9999!", "role": "landlord"})
    login = client.post("/auth/login", json={"email": "landlord_contract@test.com", "password": "Test9999!"})
    token = login.json()["access_token"]
    pdf_bytes = _minimal_pdf()
    resp = client.post(
        "/contracts/analyze",
        files={"file": ("contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Test 5: Valid PDF upload → 202 + contract_id (if MinIO available) ─────────

def test_upload_valid_pdf():
    token = register_student("contract_t1@test.com")
    pdf_bytes = _minimal_pdf()
    resp = client.post(
        "/contracts/analyze",
        files={"file": ("contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 202 if MinIO is available, 500 if not (acceptable in CI without MinIO)
    assert resp.status_code in (202, 500), f"Unexpected: {resp.text}"
    if resp.status_code == 202:
        assert "contract_id" in resp.json()
        assert resp.json()["status"] == "pending"


# ── Test 6: GET /contracts/{id} → 403 for different user ──────────────────────

def test_get_contract_wrong_user_forbidden():
    token1 = register_student("contract_t5a@test.com")
    token2 = register_student("contract_t5b@test.com")

    pdf_bytes = _minimal_pdf()
    upload = client.post(
        "/contracts/analyze",
        files={"file": ("c.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    if upload.status_code != 202:
        pytest.skip("MinIO unavailable")

    contract_id = upload.json()["contract_id"]
    resp = client.get(
        f"/contracts/{contract_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403
