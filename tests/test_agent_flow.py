"""Integration tests for Phase 2b: LangGraph agent endpoints.
Uses sync TestClient (streaming via iter_lines). BGE-M3 not required for basic flow tests.

LLM calls are mocked via monkeypatch on modules.agent.graph.call_llm / stream_llm.
This keeps these tests fast, deterministic, and free of real Anthropic/Groq API
usage — and, critically, it lets us assert on the *actual* content the pipeline
produced instead of just "some non-empty SSE payload arrived". Without this, a
fully-broken LLM fallback chain (all providers down) returns the canned
"Service temporarily unavailable" message, which is non-empty and would pass a
weaker assertion just as easily as a real recommendation would.
"""
import uuid

from starlette.testclient import TestClient

from app.main import app
from modules.agent import graph as agent_graph

client = TestClient(app, raise_server_exceptions=True)


def register_student(email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "Test9999!", "role": "student"})
    resp = client.post("/auth/login", json={"email": email, "password": "Test9999!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def mock_llm(monkeypatch, *, stream_tokens=None, stream_raises=None, intent_json="{}"):
    """Patch the LLM calls used by the agent graph.

    - call_llm is used for parse_intent (Node 1) and summarize_session (background)
    - stream_llm is used for the final streaming recommendation (Node 4)
    """
    monkeypatch.setattr(agent_graph, "call_llm", lambda task, prompt, **kwargs: intent_json)

    if stream_raises is not None:
        def _raising_stream_llm(task, prompt, **kwargs):
            raise stream_raises
        monkeypatch.setattr(agent_graph, "stream_llm", _raising_stream_llm)
    else:
        tokens = stream_tokens if stream_tokens is not None else ["MARKER_TOKEN_ALPHA ", "MARKER_TOKEN_BETA"]

        def _fake_stream_llm(task, prompt, **kwargs):
            yield from tokens
        monkeypatch.setattr(agent_graph, "stream_llm", _fake_stream_llm)


def _stream_chat(token: str, query: str, session_id: str | None = None) -> str:
    with client.stream(
        "POST", "/agent/chat",
        json={"query": query, "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        chunks = []
        for line in resp.iter_lines():
            if line.startswith("data:") and "[DONE]" not in line:
                chunks.append(line[5:].strip())
            if "[DONE]" in line:
                break
    return " ".join(chunks)


# ── Test 1: Chat requires auth ────────────────────────────────────────────────

def test_chat_requires_auth():
    resp = client.post("/agent/chat", json={"query": "show listings", "session_id": None})
    assert resp.status_code == 401


# ── Test 2: Chat streams the actual LLM-generated content ────────────────────

def test_chat_streams_real_llm_content(monkeypatch):
    """The SSE stream must carry the real LLM output, not just any non-empty payload.

    Regression guard: this used to only check `len(data_lines) >= 1`, which passed
    even when every LLM provider failed and the pipeline fell back to the canned
    "Service temporarily unavailable" message.
    """
    mock_llm(monkeypatch)
    token = register_student("agent_t1@test.com")
    full = _stream_chat(token, "apartments in Hamra under 700 USD")

    assert "MARKER_TOKEN_ALPHA" in full
    assert "MARKER_TOKEN_BETA" in full
    assert "Service temporarily unavailable" not in full


# ── Test 3: Graceful degradation when the LLM chain fully fails ──────────────

def test_chat_falls_back_gracefully_when_llm_fails(monkeypatch):
    """When the streaming LLM call raises (e.g. every provider is down), the
    pipeline must still return the canonical graceful-degradation message
    instead of crashing, hanging, or silently returning nothing.
    """
    mock_llm(monkeypatch, stream_raises=RuntimeError("simulated total provider outage"))
    token = register_student("agent_t2@test.com")
    full = _stream_chat(token, "apartments in Hamra under 700 USD").lower()

    assert "review the results above" in full
    assert "marker_token" not in full


# ── Test 4: Graceful response on no-match query ───────────────────────────────

def test_chat_graceful_on_no_match(monkeypatch):
    """An impossible price filter (max_price=1) must short-circuit to the
    canonical no-match message without ever needing a streaming LLM call.

    intent_json hardcodes max_price=1 rather than relying on the (mocked)
    LLM to parse "$1/month" out of the query — since call_llm is stubbed,
    the query text alone can no longer produce that constraint.
    """
    mock_llm(monkeypatch, intent_json='{"max_price": 1}')
    token = register_student("agent_t3@test.com")
    full = _stream_chat(token, "apartment for 1 USD per month").lower()

    assert "couldn't find any listings" in full
    assert "marker_token" not in full


# ── Test 5: Session ID is accepted ───────────────────────────────────────────

def test_chat_with_explicit_session_id(monkeypatch):
    mock_llm(monkeypatch)
    token = register_student("agent_t4@test.com")
    session_id = str(uuid.uuid4())
    full = _stream_chat(token, "listings in Gemmayzeh", session_id=session_id)
    assert "MARKER_TOKEN_ALPHA" in full


# ── Test 6: Transcribe requires auth ─────────────────────────────────────────

def test_transcribe_requires_auth():
    resp = client.post(
        "/agent/transcribe",
        files={"file": ("audio.webm", b"fake audio bytes", "audio/webm")},
    )
    assert resp.status_code == 401


# ── Test 7: Transcribe validates file extension ───────────────────────────────

def test_transcribe_rejects_invalid_extension():
    token = register_student("agent_t5@test.com")
    resp = client.post(
        "/agent/transcribe",
        files={"file": ("audio.txt", b"fake bytes", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
