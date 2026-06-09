"""Integration tests for Phase 2b: LangGraph agent endpoints.
Uses sync TestClient (streaming via iter_lines). BGE-M3 not required for basic flow tests.
"""
import uuid

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def register_student(email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "Test9999!", "role": "student"})
    resp = client.post("/auth/login", json={"email": email, "password": "Test9999!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ── Test 1: Chat requires auth ────────────────────────────────────────────────

def test_chat_requires_auth():
    resp = client.post("/agent/chat", json={"query": "show listings", "session_id": None})
    assert resp.status_code == 401


# ── Test 2: Chat endpoint returns SSE stream ──────────────────────────────────

def test_chat_returns_sse_stream():
    token = register_student("agent_t1@test.com")
    with client.stream(
        "POST", "/agent/chat",
        json={"query": "apartments in Hamra under 700 USD", "session_id": None},
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        lines = []
        for line in resp.iter_lines():
            lines.append(line)
            if "[DONE]" in line:
                break
    # Should have received at least one data line and a [DONE]
    data_lines = [line for line in lines if line.startswith("data:")]
    assert len(data_lines) >= 1


# ── Test 3: Graceful response on no-match query ───────────────────────────────

def test_chat_graceful_on_no_match():
    token = register_student("agent_t2@test.com")
    with client.stream(
        "POST", "/agent/chat",
        json={"query": "apartment for 1 USD per month", "session_id": None},
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        assert resp.status_code == 200
        chunks = []
        for line in resp.iter_lines():
            if line.startswith("data:") and "[DONE]" not in line:
                chunks.append(line[5:].strip())
            if "[DONE]" in line:
                break
    full = " ".join(chunks).lower()
    # Should be a graceful non-empty response
    assert len(full) > 5


# ── Test 4: Session ID is accepted ───────────────────────────────────────────

def test_chat_with_explicit_session_id():
    token = register_student("agent_t3@test.com")
    session_id = str(uuid.uuid4())
    with client.stream(
        "POST", "/agent/chat",
        json={"query": "listings in Gemmayzeh", "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if "[DONE]" in line:
                break


# ── Test 5: Transcribe requires auth ─────────────────────────────────────────

def test_transcribe_requires_auth():
    resp = client.post(
        "/agent/transcribe",
        files={"file": ("audio.webm", b"fake audio bytes", "audio/webm")},
    )
    assert resp.status_code == 401


# ── Test 6: Transcribe validates file extension ───────────────────────────────

def test_transcribe_rejects_invalid_extension():
    token = register_student("agent_t5@test.com")
    resp = client.post(
        "/agent/transcribe",
        files={"file": ("audio.txt", b"fake bytes", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
