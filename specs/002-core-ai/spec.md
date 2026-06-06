# Feature Specification: Phase 2 — Core AI

**Feature Branch**: `002-core-ai`

**Created**: 2026-06-05

**Status**: Draft

**Scope**: Days 4–7. BGE-M3 embeddings, LangGraph agent + MCP, fraud detection, contract analyzer, SSE notifications. Requires Phase 1 complete.

---

## User Scenarios & Testing

### User Story 1 — Student Uses AI Agent to Find Listings (Priority: P1)

A student sends a natural-language message to the agent: "2-bedroom near AUB, under $700, needs generator." The 6-node LangGraph graph parses intent, searches listings, checks fraud, calculates commutes, and returns 3 ranked options with trade-off explanations and estimated monthly costs.

**Why this priority**: The core value proposition of NestAI.

**Independent Test**: `POST /agent/chat` with a search query returns ≥1 listing with commute, area score, and fraud status.

**Acceptance Scenarios**:

1. **Given** an onboarded student, **When** they send a search query, **Then** the agent returns ranked listings with `commute_minutes`, `area_score`, `fraud_score`, and `estimated_monthly_cost`.
2. **Given** the agent cites a listing ID, **When** `validate_coherence` checkpoint runs, **Then** the ID exists in the database (no hallucinations).
3. **Given** 0 results from a narrow search, **When** `validate_results` checkpoint fires, **Then** the agent retries up to 2× with widened area/budget before responding.
4. **Given** Claude Sonnet fails, **When** the fallback chain runs, **Then** GPT-4o handles the request without a 500 error reaching the student.

---

### User Story 2 — Fraud Detection Flags Suspicious Listings (Priority: P1)

The fraud module runs automatically on new listings. A listing priced 2+ standard deviations below the neighbourhood median, with a phone number linked to 3+ other listings, and a photo matching a known scam phash, receives a "High Risk" badge with specific evidence items shown to the student.

**Why this priority**: Protects students from Lebanon's most common housing scam vector.

**Independent Test**: Submit a listing meeting fraud thresholds → verify `fraud_reports.score ≥ 0.7` and evidence JSONB contains all three flag types.

**Acceptance Scenarios**:

1. **Given** a listing with price z-score > 2.0, **When** the fraud check runs, **Then** `fraud_reports.price_zscore` is stored and `score` reflects it.
2. **Given** a photo with phash hamming distance ≤ 10 from a known fraud photo, **When** the Celery dedup task runs, **Then** `photo_flags` is populated in `fraud_reports.evidence`.
3. **Given** a phone number linked to 2+ other listings, **When** a new listing is submitted, **Then** `phone_flags` is added to the evidence.

---

### User Story 3 — Contract Analyzer Flags Risky Lease Clauses (Priority: P1)

A student uploads a PDF lease. PyMuPDF extracts text; if empty (scanned doc), GPT-4o Vision OCR runs as fallback. Claude Sonnet returns a structured risk report with high/medium/low severity per clause.

**Why this priority**: Lebanese leases are designed to favour landlords — hidden fees and automatic eviction clauses are common.

**Independent Test**: Upload a PDF with a known red-flag clause → verify `analysis.risk_items` contains at least one `"level": "high"` entry.

**Acceptance Scenarios**:

1. **Given** a text-extractable PDF, **When** `POST /contracts/analyze` is called, **Then** `risk_items` contains objects with `level`, `clause_text`, and `explanation`.
2. **Given** a scanned PDF (PyMuPDF returns empty), **When** the OCR fallback runs, **Then** `contracts.ocr_used = true` and the same `risk_items` schema is returned.
3. **Given** a contract analysis in progress, **When** the student polls status, **Then** `contracts.status` progresses through `pending → ocr_running (if needed) → complete`.

---

### User Story 4 — Roommate Matching Shows 5-Dimension Scores (Priority: P2)

After onboarding, a student's 1024-dim BGE-M3 profile embedding is computed. The roommate module returns potential matches with five dimension scores (sleep, study, cleanliness, guests, budget) as individual values — not just a total.

**Why this priority**: A total score is not actionable; dimension scores let students make informed trade-offs.

**Independent Test**: Two profiles with contrasting sleep schedules → `sleep` dimension score < 0.5.

**Acceptance Scenarios**:

1. **Given** two student profiles with embeddings, **When** `GET /roommate/matches` is called, **Then** response includes `score` and `dimensions: {sleep, study, cleanliness, guests, budget}`.
2. **Given** a student sends a roommate request, **When** the recipient accepts, **Then** both receive an SSE notification via Redis pub/sub.

---

### User Story 5 — Real-Time Notifications via SSE (Priority: P2)

When a new listing matching a student's saved filters is posted, or a roommate request is received, the student gets a push notification without refreshing the page — delivered via SSE over a persistent HTTP connection.

**Why this priority**: Real-time feedback on a mobile/low-bandwidth connection requires SSE not WebSockets.

**Independent Test**: Open `GET /notifications/stream`, trigger a notification via Redis pub/sub, verify the SSE event arrives.

**Acceptance Scenarios**:

1. **Given** an authenticated student connected to `GET /notifications/stream`, **When** a Redis `sse:{user_id}` message is published, **Then** the SSE event is received within 1 second.
2. **Given** a disconnection, **When** the student reconnects, **Then** unread notifications are delivered from `notifications` table.

---

### Edge Cases

- Agent query with no results after 2x retry widening — what message does the student receive?
- Contract PDF is password-protected — system should return a clear error, not hang.
- BGE-M3 worker hasn't initialized yet when first embedding request arrives.
- Celery `nestai:dead` queue grows — no silent dropping allowed.
- SSE connection drops mid-stream — client should reconnect cleanly.

---

## Requirements

- **FR-001**: BGE-M3 MUST load once at `worker_init` signal. All embeddings MUST be 1024-dim.
- **FR-002**: LangGraph agent MUST have 6 nodes, 5 checkpoints, 9 MCP tools, and 3-layer memory.
- **FR-003**: All LLM calls MUST go through `core/llm_router.py` with tier routing and Redis cache check.
- **FR-004**: Fraud detection MUST run price z-score, phone dedup, and imagehash phash checks.
- **FR-005**: Contract analyzer MUST try PyMuPDF first; fall back to GPT-4o Vision only if text is empty.
- **FR-006**: SSE MUST use Redis pub/sub. WebSocket dependencies are forbidden.
- **FR-007**: Failed Celery tasks MUST go to `nestai:dead` — never silently dropped.

## Success Criteria

- **SC-001**: `pytest tests/test_agent_flow.py -v` — all agent behavior tests pass.
- **SC-002**: `pytest tests/test_embeddings.py -v` — dimension (1024), normalize, batch tests pass.
- **SC-003**: `docker compose --profile spec run spec-validator` exits 0.
- **SC-004**: A full agent conversation (search → compare → explain) completes in ≤8s p95.

## Assumptions

- Phase 1 is complete and passing.
- OpenAI API key and Anthropic API key are set in `.env`.
- OSRM routing server is running (seeded with Lebanon OSM data).
- BGE-M3 model files are available locally (downloaded at worker startup).
