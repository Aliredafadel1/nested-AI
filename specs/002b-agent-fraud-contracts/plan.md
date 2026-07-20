# Implementation Plan: Phase 2b — Agent, Fraud, Contracts, SSE

**Status**: Ready to implement
**Based on**: specs/002b-agent-fraud-contracts/spec.md (clarified 2026-06-06)
**Depends on**: Phase 2a complete — MiniLM embeddings, roommate module

---

## Constitution Check

| Principle | Status |
|-----------|--------|
| Module boundaries — no cross-repository imports | ✓ All cross-module calls go through service.py (see §1) |
| All LLM calls through core/llm_router.py | ✓ No new external SDK calls outside llm_router.py |
| No WebSocket dependencies | ✓ SSE + Redis pub/sub only |
| Security — prompt injection sanitizer before every LLM call | ✓ Required in agent.service before parse_intent and compare nodes |
| Real DB in tests | ✓ All three new test files hit real containerized PostgreSQL |
| Spec-before-code | ✓ This plan gates /nest-tasks |

---

## 1. Architecture Decisions

### Six New Full Module Implementations

Each module gets the standard 5-file layout plus a `tasks.py` where async work applies:

| Module | New files |
|--------|-----------|
| agent | models.py, schemas.py, repository.py, service.py, router.py, tasks.py, graph.py, tools.py |
| fraud | models.py, schemas.py, repository.py, service.py, router.py, tasks.py |
| contracts | models.py, schemas.py, repository.py, service.py, router.py, tasks.py |
| area_intel | models.py, schemas.py, repository.py, service.py, router.py |
| estimator | models.py, schemas.py, repository.py, service.py, router.py |
| notifications | models.py, schemas.py, repository.py, service.py, router.py |

### Cross-Module Service Calls (no repository imports — NON-NEGOTIABLE)

| Caller module | Needs data from | Calls method on |
|---------------|----------------|-----------------|
| agent.service (search_listings tool) | listings with embeddings | housing.service.semantic_search(embedding, filters) |
| agent.service (get_area_scores tool) | neighbourhood scores | area_intel.service.get_by_name(name) |
| agent.service (check_fraud tool) | fraud report | fraud.service.get_report(listing_id) |
| agent.service (estimate_cost tool) | cost breakdown | estimator.service.calculate(rent, neighbourhood_id, university_id) |
| agent.service (get_roommate_matches tool) | match list | roommate.service.get_matches(db, user_id) |
| agent.service (compare_areas tool) | two neighbourhoods | area_intel.service.compare(area_a, area_b) |
| fraud.service (price z-score) | listing price + neighbourhood | housing.service.get_listing(listing_id), housing.service.get_neighbourhood_stats(neighbourhood_id) |
| fraud.service (phone dedup) | landlord listing count | housing.service.get_landlord_listing_count(landlord_id) |
| fraud.service (photo phash) | photo phash values | housing.service.get_listing_photo_phashes(listing_id) |

### New Methods Added to Existing Services

`modules/housing/service.py` — 4 new methods:
- `semantic_search(query_embedding: list[float], filters: dict, limit: int = 10) -> list[Listing]`
- `get_neighbourhood_stats(neighbourhood_id: int) -> dict` — returns {median_price, stddev_price}
- `get_landlord_listing_count(landlord_id: int) -> int`
- `get_listing_photo_phashes(listing_id: int) -> list[str]`

`modules/housing/repository.py` — 4 matching query methods added.

### LangGraph Agent Graph Design

```
parse_intent → search_and_rank → validate_results → compare → validate_comparison → explain_and_respond
                                      ↑__(retry_count < 2)__↓
```

State type:
```python
{
    "query": str,
    "session_id": str,
    "intent": dict,          # budget, area, must_haves extracted by GPT-4o mini
    "listings": list,        # list of listing dicts from search_and_rank
    "retry_count": int,      # incremented in validate_results on empty results
    "comparison": str | None,  # Claude Sonnet comparison text from compare node
    "response": str | None,    # final answer from explain_and_respond
    "errors": list[str],     # non-fatal warnings (e.g. OSRM unavailable)
}
```

Node responsibilities:
- **parse_intent**: `call_llm("parse_intent", query)` → structured intent dict
- **search_and_rank**: calls search_listings + calculate_commute + get_area_scores + check_fraud MCP tools; assembles listings list
- **validate_results**: if len(listings) == 0 and retry_count < 2, widen filters and return to search_and_rank; else continue
- **compare**: `call_llm("agent_compare_explain", context)` with top 3 listings → comparison string
- **validate_comparison**: `call_llm("validate_coherence", comparison)` verifies every listing_id cited actually exists in DB via agent.repository.listing_exists(); if fake IDs detected, clears comparison and re-runs compare node (once)
- **explain_and_respond**: uses `stream_llm("agent_compare_explain", final_prompt)` for token-level SSE; saves session to Redis (full state) and PostgreSQL (history + GPT-4o mini summary)

### SSE Streaming for Agent Chat

`POST /agent/chat` returns `StreamingResponse(media_type="text/event-stream")`:
1. Nodes 1–5 run to completion inside the async handler
2. Node 6 calls `stream_llm("agent_compare_explain", prompt)` which uses Anthropic streaming API
3. Each token chunk is yielded as `data: <token>\n\n`
4. Final event: `data: [DONE]\n\n`
5. Session persistence to Redis + PostgreSQL after stream completes

### SSE Notifications Stream

`GET /notifications/stream` — async generator pattern:
1. On connect: flush all unread notifications from `notifications` table as SSE events
2. Subscribe to `sse:{user_id}` Redis pub/sub channel
3. Yield pub/sub messages as SSE events until client disconnects
4. On disconnect: unsubscribe cleanly

---

## 2. Database Changes

**No new migration file required.** All Phase 2b tables exist in `migrations/init.sql`:
`agent_sessions`, `student_memory`, `rag_chunks`, `fraud_reports`, `contracts`, `cost_estimates`, `notifications`

**One data task**: Create `seed/rag_chunks.sql` with 20–30 Lebanon housing FAQ rows for the `survival_search` MCP tool:
- Generator companies by neighbourhood (Hamra, Gemmayzeh, Achrafieh, etc.)
- Water delivery services (tanker companies, typical cost)
- 24h pharmacies by area
- EDL power schedule lookups
- Internet providers (Ogero, WT, IDM)
All rows: `source_type = 'housing_faq'`, `language` one of 'en'/'ar'/'fr'.
Embeddings for rag_chunks seeded via the `index_rag_chunk` Celery task at startup.

---

## 3. API Contracts

### Agent Module (`/agent`)

```
POST /agent/chat
  auth: bearer(student)
  request:  { query: str, session_id: str | null }
  response: StreamingResponse (text/event-stream)
    — events: data: <token>\n\n  ...  data: [DONE]\n\n
  errors: 401, 429

POST /agent/transcribe
  auth: bearer(student)
  request:  multipart/form-data  audio (max 25MB, .webm/.mp4/.wav/.m4a)
  response: { text: str }
  errors: 400 (invalid format or empty), 401, 413
```

### Fraud Module (`/fraud`)

```
GET /fraud/{listing_id}
  auth: optional
  response: {
    listing_id: int,
    score: float,          # 0.0–1.0
    price_zscore: float | null,
    evidence: {
      price_flags: list[str],
      phone_flags: list[str],
      photo_flags: list[str],
      text_flags:  list[str]   # qualitative only, does not affect numeric score
    },
    computed_at: datetime
  }
  cache: Redis fraud:{listing_id} Hash, 12h TTL — returned without recomputing on hit
  errors: 404
```

### Contracts Module (`/contracts`)

```
POST /contracts/analyze
  auth: bearer(student)
  request:  multipart/form-data  PDF (max 10MB)
  response: { contract_id: int, status: "pending" }
  errors:
    400 — file > 10MB (rejected before MinIO write)
    400 — not a PDF (magic bytes check)
    400 — password-protected PDF (detected by PyMuPDF, no hang)
    401

GET /contracts/{id}
  auth: bearer(student, own)
  response: {
    id: int,
    ocr_used: bool,
    status: "pending" | "ocr_running" | "analyzing" | "complete" | "failed",
    analysis: {
      risk_items: [
        { level: "high"|"medium"|"low", clause_text: str, explanation: str }
      ]
    } | null,
    created_at: datetime
  }
  errors: 401, 403, 404
```

### Area Intel Module (`/areas`)

```
GET /areas/{name}
  auth: optional
  response: {
    id: int, name: str, name_ar: str | null,
    electricity_hours: float,    # avg EDL hours/day
    generator_cost: int,         # USD/month
    internet: int,               # 1–5
    transport: int,              # 1–5
    safety: int,                 # 1–5
    student_vibe: int            # 1–5
  }
  cache: Redis area:{neighbourhood_id} Hash, 24h TTL
  errors: 404

POST /areas/compare
  auth: optional
  request:  { area_a: str, area_b: str }
  response: { area_a: NeighborhoodOut, area_b: NeighborhoodOut }
  errors: 404 (either area not found)
```

### Estimator Module (`/estimator`)

```
POST /estimator/calculate
  auth: bearer(student)
  request:  { rent: int, neighbourhood_id: int, university_id: int | null }
  response: {
    rent: int,
    generator: int,       # from neighborhoods.generator_cost
    water: int,           # fixed 15 USD (Lebanon tanker average)
    internet: int,        # fixed 30 USD
    transport: int,       # OSRM-based estimate or neighbourhood default
    total_monthly: int,
    commute_minutes: int | null  # null if OSRM unavailable
  }
  errors: 400 (invalid neighbourhood_id), 401
  note: saves result to cost_estimates table
```

### Notifications Module (`/notifications`)

```
GET /notifications/stream
  auth: bearer(student)
  response: text/event-stream
    — on connect: all unread notifications from DB as SSE events
    — ongoing: Redis pub/sub sse:{user_id} messages
    — event format: data: {"id":int,"type":str,"payload":{},"created_at":str}\n\n

GET /notifications
  auth: bearer(student)
  response: list[{ id, type, payload, read, created_at }]
  status: 200

POST /notifications/{id}/read
  auth: bearer(student, own)
  status: 204
  errors: 403, 404
```

---

## 4. LLM Routing

All task names are already in `TASK_TIERS`. Zero new additions to the dict.

| Task | Tier | Model | Used in |
|------|------|-------|---------|
| `parse_intent` | cheap | GPT-4o mini | agent graph node 1 |
| `agent_compare_explain` | powerful | Claude Sonnet | agent graph node 6 (streaming) |
| `validate_coherence` | powerful | Claude Sonnet | agent graph node 5 |
| `classify_fraud_text` | cheap | GPT-4o mini | fraud.tasks qualitative flags |
| `analyze_contract` | powerful | Claude Sonnet | contracts.tasks text-PDF path |
| `ocr_analyze_contract` | powerful | Claude Sonnet | contracts.tasks OCR path |
| `summarize_session` | cheap | GPT-4o mini | agent session end summary |
| `embed_query` | free | MiniLM | agent search_listings tool |
| `embed_rag_chunk` | free | MiniLM | agent.tasks index_rag_chunk |

### Required `core/llm_router.py` updates (4 changes)

1. **Fix `_call_free`**: Replace inline `SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")` load with
   `from core.embeddings import embed_text; return embed_text(prompt)`.
   This makes free-tier use the worker-level singleton, not load per-call.

2. **Add `stream_llm(task, prompt, **kwargs) -> Iterator[str]`**: Streaming variant
   for the powerful tier only. Uses `anthropic_client.messages.stream(...)` context manager,
   yields `event.delta.text` for each `text_delta` event. Raises `ValueError` if task tier ≠ powerful.

3. **Add `transcribe_audio(file_bytes: bytes, filename: str) -> str`**: Calls
   `openai_client.audio.transcriptions.create(model="whisper-1", file=(filename, file_bytes))`.
   Not routed through `call_llm` (different input type) but lives in `llm_router.py` to satisfy
   the "no SDK calls outside llm_router" invariant.

4. **Add fallback chain to `call_llm`**: wrap `_call_powerful` in try/except; on failure try
   `_call_cheap`; on failure try `_call_mini` (GPT-4o); on failure check stale Redis LLM cache
   (`llm:{task}:{prompt_hash}`, any TTL); on total failure return a graceful user-facing message
   string. Log each step at WARN. Never raise to the caller.

---

## 5. Redis Keys

All keys exist in `RedisKeys`. No new key patterns needed.

| Pattern | Purpose | TTL |
|---------|---------|-----|
| `session:{user_id}:{session_id}` | agent live state during conversation | 2h |
| `llm:{task}:{prompt_hash}` | LLM response cache (stale fallback source) | 6h |
| `fraud:{listing_id}` | cached fraud report | 12h |
| `area:{neighbourhood_id}` | cached neighbourhood scores | 24h |
| `commute:{listing_id}:{university_id}` | cached OSRM result | 1h |
| `contract:{contract_id}:status` | contract analysis status polling | 1h |
| `sse:{user_id}` | SSE pub/sub channel | — (no expiry) |
| `notif:unread:{user_id}` | unread notification count | — |

---

## 6. Celery Tasks

| Task | Module | Queue | Timeout | Retry policy |
|------|--------|-------|---------|-------------|
| `run_fraud_check(listing_id)` | fraud.tasks | `nestai:medium` | 120s | autoretry 3×, backoff |
| `analyze_contract_async(contract_id)` | contracts.tasks | `nestai:high` | 300s | autoretry 2×, backoff |
| `index_rag_chunk(chunk_id)` | agent.tasks | `nestai:low` | 60s | autoretry 3×, backoff |
| `seed_rag_embeddings()` | agent.tasks | `nestai:low` | 600s | manual trigger only |

**Trigger wiring**:
- `housing.service.create_listing()` already calls `embed_listing.delay()` — add `run_fraud_check.delay(listing_id)` after it
- `contracts.service.create_contract()` calls `analyze_contract_async.delay(contract_id)` after MinIO upload
- `seed_rag_embeddings` runs once manually after `seed/rag_chunks.sql` is applied

**`core/celery_config.py` updates**:
- Add to `include=` list: `"modules.fraud.tasks"`, `"modules.contracts.tasks"`, `"modules.agent.tasks"`
- Add to `task_routes`:
  ```python
  "modules.fraud.tasks.run_fraud_check":            {"queue": "nestai:medium"},
  "modules.contracts.tasks.analyze_contract_async": {"queue": "nestai:high"},
  "modules.agent.tasks.index_rag_chunk":            {"queue": "nestai:low"},
  "modules.agent.tasks.seed_rag_embeddings":        {"queue": "nestai:low"},
  ```

---

## 7. Module Boundary Check

| Module | Owns tables | Repository queries | Cross-module access |
|--------|------------|-------------------|---------------------|
| agent | agent_sessions, student_memory, rag_chunks | reads/writes all three | calls housing/fraud/area_intel/estimator/roommate **service** only |
| fraud | fraud_reports | reads/writes fraud_reports | calls housing.service for listing data |
| contracts | contracts | reads/writes contracts | none — self-contained |
| area_intel | neighborhoods | reads neighborhoods | none — self-contained |
| estimator | cost_estimates | reads neighborhoods (via area_intel.service), writes cost_estimates | calls area_intel.service for generator_cost; HTTP call to OSRM |
| notifications | notifications | reads/writes notifications | none — self-contained |

**Zero cross-repository imports.** `grep "from modules.*repository import" modules/` must return zero hits outside each module's own directory.

---

## 8. Test Plan

### `tests/test_agent_flow.py` (new file, 6 tests)

- `test_parse_intent_extracts_fields` — POST /agent/chat with "2-bedroom in Hamra under 700 USD" → response cites Hamra, budget ≤700, bedrooms=2
- `test_validate_results_retries_on_empty` — craft a query with no matches → verify retry_count=2 in final state, response is graceful "no matches" message
- `test_validate_comparison_rejects_hallucinated_id` — inject a fake listing_id into compare output → verify validate_comparison fires regeneration
- `test_full_conversation_persisted` — run full graph → verify agent_sessions row written to PostgreSQL with history and summary
- `test_survival_search_returns_chunks` — POST /agent/chat "generator companies in Hamra" → response references rag_chunk FAQ content
- `test_osrm_unavailable_graceful` — mock OSRM timeout → verify response contains commute "—" and no 500 error

### `tests/test_fraud.py` (new file, 5 tests)

- `test_price_zscore_flag` — create listing priced 2.5 stddev below neighbourhood median → score ≥ 0.5×price_component contribution
- `test_phone_dedup_flag` — one landlord with 3 listings → phone_flags non-empty in evidence
- `test_photo_phash_flag` — two listing photos with hamming distance ≤10 → photo_flags non-empty
- `test_fraud_cache_hit` — GET /fraud/{id} twice → second call returns same score without DB recompute (verify via Redis key TTL)
- `test_score_formula_weights` — controlled inputs → verify score = 0.5×price + 0.3×phone + 0.2×photo exactly

### `tests/test_contracts.py` (new file, 4 tests)

- `test_text_pdf_analysis` — upload a text-extractable PDF with a known clause → risk_items contains ≥1 high-level item with clause_text + explanation
- `test_scanned_pdf_ocr_fallback` — upload blank-text PDF (image only) → contracts.ocr_used=true, same risk_items schema returned
- `test_pdf_too_large_rejected` — upload 11MB file → 400 before MinIO write
- `test_password_protected_pdf` — upload encrypted PDF → 400 response within 5s (no hang)

---

## 9. Files Created / Modified

### New files
```
modules/agent/models.py
modules/agent/schemas.py
modules/agent/repository.py        # owns: agent_sessions, student_memory, rag_chunks
modules/agent/service.py           # LangGraph orchestration + session management
modules/agent/router.py            # POST /agent/chat, POST /agent/transcribe
modules/agent/graph.py             # LangGraph StateGraph definition (6 nodes)
modules/agent/tools.py             # 9 MCP tool functions
modules/agent/tasks.py             # index_rag_chunk, seed_rag_embeddings

modules/fraud/models.py
modules/fraud/schemas.py
modules/fraud/repository.py        # owns: fraud_reports
modules/fraud/service.py           # 3-signal fraud scoring
modules/fraud/router.py            # GET /fraud/{listing_id}
modules/fraud/tasks.py             # run_fraud_check

modules/contracts/models.py
modules/contracts/schemas.py
modules/contracts/repository.py    # owns: contracts
modules/contracts/service.py       # PyMuPDF + OCR path
modules/contracts/router.py        # POST /contracts/analyze, GET /contracts/{id}
modules/contracts/tasks.py         # analyze_contract_async

modules/area_intel/models.py
modules/area_intel/schemas.py
modules/area_intel/repository.py   # owns: neighborhoods (read-only in this phase)
modules/area_intel/service.py      # get_by_name, compare, Redis caching
modules/area_intel/router.py       # GET /areas/{name}, POST /areas/compare

modules/estimator/models.py
modules/estimator/schemas.py
modules/estimator/repository.py    # owns: cost_estimates
modules/estimator/service.py       # cost breakdown + OSRM call
modules/estimator/router.py        # POST /estimator/calculate

modules/notifications/models.py
modules/notifications/schemas.py
modules/notifications/repository.py # owns: notifications
modules/notifications/service.py    # pub/sub + unread delivery
modules/notifications/router.py    # GET /notifications/stream, GET /notifications, POST /notifications/{id}/read

seed/rag_chunks.sql                 # 20–30 Lebanon housing FAQ rows

tests/test_agent_flow.py
tests/test_fraud.py
tests/test_contracts.py
```

### Modified files
```
core/llm_router.py              # fix _call_free, add stream_llm, add transcribe_audio, add fallback chain
core/celery_config.py           # add fraud/contracts/agent tasks to include= and task_routes
modules/housing/service.py      # add semantic_search, get_neighbourhood_stats, get_landlord_listing_count, get_listing_photo_phashes
modules/housing/service.py      # trigger run_fraud_check.delay after create_listing
modules/housing/repository.py   # add 4 new query methods
app/main.py                     # include_router for 6 new modules
specs/all_modules.yaml          # fill in all 6 pending modules with endpoint contracts
```

---

Run `/nest-tasks` to generate the ordered task breakdown.
