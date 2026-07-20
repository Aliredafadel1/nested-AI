# Feature Specification: Phase 2b — Agent, Fraud, Contracts, SSE

**Feature Branch**: `002b-agent-fraud-contracts`

**Created**: 2026-06-05

**Status**: Draft

**Scope**: Days 5–7. LangGraph agent + 9 MCP tools, fraud detection, area intelligence, contract analyzer (PyMuPDF + OCR fallback), real-time SSE notifications. Requires Phase 2a complete.

---

## Clarifications

### Session 2026-06-06

- Q: What does the `survival_search` MCP tool do? → A: Option B — Lebanon-specific survival queries. Searches `rag_chunks` table (source_type = 'housing_faq') for practical urban survival info: generator companies by neighbourhood, water delivery services, 24h pharmacies, EDL power schedule lookups, internet providers. Input: free-text query. Output: top 3 matching RAG chunks with source and text.
- Q: What happens when OSRM is unavailable for `calculate_commute`? → A: Option B — graceful null. Returns `{"commute_minutes": null, "note": "Commute data temporarily unavailable"}`. Agent continues and responds with listing data; commute displayed as "—" in UI. No retry, no blocking.
- Q: How are the 3 fraud signals combined into `fraud_reports.score`? → A: Option B — weighted formula: `score = 0.5 × price_component + 0.3 × phone_component + 0.2 × photo_component`. `classify_fraud_text` (GPT-4o mini) produces `text_flags` as a 4th input to the evidence JSONB but does NOT contribute to the numeric score directly — text flags are qualitative evidence only.
- Q: What fields does the LangGraph agent state schema carry between nodes? → A: Option B — `{query: str, session_id: str, intent: dict, listings: list, retry_count: int, comparison: str | None, response: str | None, errors: list[str]}`. `retry_count` tracks validate-node retry loops (max 2). `errors` accumulates non-fatal warnings (e.g. OSRM unavailable) surfaced in the final response.
- Q: What is the Redis vs PostgreSQL boundary for agent session state? → A: Option A — hot/cold split. Redis holds the full live state dict during a conversation (`session:{user_id}:{session_id}`, 2h TTL). Nodes read/write Redis ONLY during a conversation. PostgreSQL `agent_sessions` row is written ONCE at conversation end: `history` (list of turns) + `summary` (GPT-4o mini generated). PostgreSQL is the permanent audit trail; Redis is the live working memory.

---

## User Scenarios & Testing

### User Story 1 — AI Agent Searches and Ranks Listings (Priority: P1)

A student sends a natural-language query. The 6-node LangGraph graph parses intent, calls MCP tools (search, commute, area scores, fraud check), validates results (retrying up to 2× if empty), compares top listings, validates the comparison (no hallucinated IDs), and responds in natural language. Session state is persisted in Redis (2h) and PostgreSQL (permanent).

**Why this priority**: The core value proposition of the entire platform.

**Independent Test**: `POST /agent/chat` with a search query → response contains ≥1 listing with commute, area score, fraud status — all IDs verified to exist in DB.

**Acceptance Scenarios**:

1. **Given** a student query with clear intent, **When** the agent runs, **Then** `parse_intent` extracts budget, area, and must-haves correctly.
2. **Given** no listings match the initial query, **When** `validate_results` fires, **Then** the agent retries up to 2× widening area and budget before responding.
3. **Given** the agent's `compare` node produces a response, **When** `validate_comparison` runs, **Then** every cited listing ID is verified against the database — hallucinated IDs cause regeneration.
4. **Given** Claude Sonnet fails, **When** the fallback chain runs, **Then** GPT-4o takes over without a 500 error reaching the student.
5. **Given** a completed conversation, **When** `explain_and_respond` finishes, **Then** `agent_sessions.history` (turn list) and `summary` are persisted to PostgreSQL. During the conversation all state is in Redis only (`session:{user_id}:{session_id}`, 2h TTL).

---

### User Story 2 — Fraud Detection Flags Suspicious Listings (Priority: P1)

The fraud module runs automatically on new listings via Celery. Three signals are checked: price z-score vs neighbourhood median, phone number deduplication across all listings, and perceptual photo hash similarity against known fraud images. Results are stored with evidence.

**Why this priority**: The most common harm to Lebanese students is financial fraud via fake listings.

**Independent Test**: Create a listing meeting all 3 fraud thresholds → `fraud_reports.score ≥ 0.7` and evidence JSONB contains all three flag types.

**Acceptance Scenarios**:

1. **Given** a listing with price > 2.0 standard deviations below neighbourhood median, **When** the fraud check runs, **Then** `fraud_reports.price_zscore` is stored and the score reflects it.
2. **Given** a photo with phash hamming distance ≤ 10 from a known fraud photo, **When** the Celery dedup task runs, **Then** `photo_flags` is added to `fraud_reports.evidence`.
3. **Given** a phone number already linked to 2+ other listings, **When** a new listing is submitted with that number, **Then** `phone_flags` is added to the evidence.
4. **Given** `GET /fraud/{listing_id}` is called, **When** a cached fraud score exists (`fraud:{listing_id}` Redis Hash, 12h TTL), **Then** the cached value is returned without recomputing.

---

### User Story 3 — Contract Analyzer Returns Structured Risk Report (Priority: P1)

A student uploads a PDF lease. PyMuPDF extracts text. If the extraction returns empty (scanned/image PDF), GPT-4o Vision OCR processes the images as fallback. Claude Sonnet analyzes the text and returns structured risk items grouped by severity.

**Why this priority**: Lebanese leases routinely contain clauses that are harmful to tenants — hidden fees, auto-eviction, ambiguous renewal.

**Independent Test**: Upload a test PDF with a known red-flag clause → `contracts.analysis.risk_items` contains ≥1 `"level": "high"` item. Upload a blank-text scanned PDF → `contracts.ocr_used = true` and same schema is returned.

**Acceptance Scenarios**:

1. **Given** a text-extractable PDF, **When** `POST /contracts/analyze` is called, **Then** `risk_items` contains objects with `level` (high/medium/low), `clause_text`, and `explanation`.
2. **Given** a scanned PDF where PyMuPDF returns empty text, **When** the OCR fallback runs, **Then** `contracts.ocr_used = true` and the same `risk_items` schema is returned.
3. **Given** a contract analysis in progress, **When** `contracts.status` is polled, **Then** it transitions: `pending → ocr_running (if needed) → complete`.
4. **Given** a PDF > 10MB, **When** the upload is attempted, **Then** a 400 error is returned before the file reaches MinIO.

---

### User Story 4 — Area Intelligence Scores Neighbourhoods (Priority: P2)

The area intelligence module stores electricity hours, generator cost, internet quality, transport, safety, and student vibe per neighbourhood. Students can retrieve scores for one area or compare two side-by-side.

**Why this priority**: No other platform in Lebanon surfaces neighbourhood-level generator and electricity data.

**Independent Test**: `GET /areas/hamra` returns all 6 score dimensions. `POST /areas/compare` with two neighbourhood names returns side-by-side scores.

**Acceptance Scenarios**:

1. **Given** a seeded neighbourhood, **When** `GET /areas/{name}` is called, **Then** the response includes `electricity_hours`, `generator_cost`, `internet`, `transport`, `safety`, `student_vibe`.
2. **Given** two neighbourhood names, **When** `POST /areas/compare` is called, **Then** both neighbourhoods' scores are returned in one response.
3. **Given** `area:{neighbourhood_id}` Redis Hash exists (24h TTL), **When** `GET /areas/{name}` is called, **Then** the cached value is returned without hitting PostgreSQL.

---

### User Story 5 — Real-Time SSE Notifications Are Delivered (Priority: P2)

Students receive push notifications (new matching listing, roommate request accepted, fraud flag update) over a persistent SSE connection backed by Redis pub/sub.

**Why this priority**: Mobile students need real-time updates without polling. WebSockets are out of scope — SSE is simpler and sufficient.

**Independent Test**: Connect to `GET /notifications/stream`, publish to `sse:{user_id}` Redis channel, verify the SSE event arrives within 1 second.

**Acceptance Scenarios**:

1. **Given** a student connected to `GET /notifications/stream`, **When** a message is published to `sse:{user_id}`, **Then** the SSE event arrives within 1 second.
2. **Given** a student disconnects and reconnects, **When** unread notifications exist in the `notifications` table, **Then** they are delivered on reconnect.
3. **Given** a WebSocket import is added anywhere in the codebase, **When** a code review runs, **Then** it is flagged and rejected.

---

### Edge Cases

- Agent session expires (Redis 2h TTL) mid-conversation — student should get a clean "session expired" response, not a 500.
- OSRM unavailable — `calculate_commute` returns `{"commute_minutes": null, "note": "Commute data temporarily unavailable"}`. Agent continues without commute data; displayed as "—" in UI.
- All 3 LLM providers fail simultaneously — fallback chain must serve stale Redis cache and show a human message.
- Contract PDF is password-protected — return 400 with a clear message, do not hang waiting for PyMuPDF.
- Celery `nestai:dead` queue grows — never silently dropped; monitored via Flower.
- SSE connection drops on mobile network switch — client should reconnect cleanly.

---

## Requirements

- **FR-001**: LangGraph agent MUST have exactly 6 nodes (`parse_intent`, `search_and_rank`, `validate_results`, `compare`, `validate_comparison`, `explain_and_respond`) and 5 checkpoints. State schema: `{query: str, session_id: str, intent: dict, listings: list, retry_count: int, comparison: str | None, response: str | None, errors: list[str]}`.
- **FR-002**: Agent MUST support 9 MCP tools: `search_listings`, `calculate_commute`, `get_area_scores`, `check_fraud`, `get_roommate_matches`, `estimate_cost`, `compare_areas`, `transcribe_audio`, `survival_search`. The `survival_search` tool performs semantic search over `rag_chunks` (source_type = 'housing_faq') and returns top 3 matches for Lebanon urban survival queries (generator companies, water delivery, pharmacies, power schedules, ISPs).
- **FR-003**: All LLM calls MUST go through `core/llm_router.py`. No direct OpenAI or Anthropic SDK calls outside that file.
- **FR-004**: `validate_coherence` MUST verify all cited listing IDs exist in the DB before any response reaches the student.
- **FR-005**: Fraud detection MUST run price z-score, phone dedup, and imagehash phash checks. Score formula: `score = 0.5 × price_component + 0.3 × phone_component + 0.2 × photo_component` (each component normalized 0–1). `classify_fraud_text` (GPT-4o mini) produces qualitative `text_flags` stored in `evidence` JSONB but does not contribute to the numeric score.
- **FR-006**: Contract analyzer MUST try PyMuPDF first; GPT-4o Vision fallback ONLY if PyMuPDF returns empty text.
- **FR-007**: SSE MUST use Redis pub/sub. WebSocket dependencies are forbidden anywhere in the codebase.
- **FR-008**: Failed Celery tasks MUST route to `nestai:dead` — never silently dropped.

## Success Criteria

- **SC-001**: `pytest tests/test_agent_flow.py -v` — all agent behavior tests pass (parse_intent, validate_results retry, full conversation, survival bypass).
- **SC-002**: `docker compose --profile spec run spec-validator` exits 0 against all module YAML contracts.
- **SC-003**: A full agent conversation (search → compare → explain) completes in ≤8s p95.
- **SC-004**: Contract analysis completes in ≤30s for a 10-page PDF (p95), including OCR fallback path.

## Assumptions

- Phase 2a is complete — MiniLM embeddings exist for listings and student profiles.
- `get_roommate_matches` MCP tool calls Phase 2a's roommate service.
- OSRM routing server is running and seeded with Lebanon OSM data.
- OpenAI API key and Anthropic API key are set in `.env`.
