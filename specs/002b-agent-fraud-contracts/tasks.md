# Tasks: Phase 2b — Agent, Fraud, Contracts, SSE

**Input**: specs/002b-agent-fraud-contracts/plan.md + spec.md
**5 User Stories** | P1: US1 (agent), US2 (fraud), US3 (contracts) | P2: US4 (area intel), US5 (SSE notifications)

---

## Phase 1: Data Seeding

**Purpose**: Seed rag_chunks for the agent's `survival_search` MCP tool. No schema migration needed — all tables exist in init.sql.

- [ ] T001 Create `seed/rag_chunks.sql` — 20–30 INSERT rows for Lebanon housing FAQs:
  - generator companies by neighbourhood (Hamra, Gemmayzeh, Achrafieh, Mar Mikhael, Verdun, Badaro, Ras Beirut, Dekwaneh)
  - water tanker delivery services and typical costs
  - 24h pharmacies by area
  - EDL power schedule info
  - Internet providers (Ogero, WT, IDM) coverage
  - All rows: `source_type = 'housing_faq'`, `embedding = NULL` (populated by Celery task)

**Checkpoint**: `docker compose exec db psql -U nestai -d nestai -f /seed/rag_chunks.sql` exits 0; `SELECT COUNT(*) FROM rag_chunks` ≥ 20

---

## Phase 2: Core Changes

**Purpose**: Update llm_router.py and celery_config.py to support Phase 2b features.

- [ ] T002 Update `core/llm_router.py` — 4 targeted changes:
  1. Fix `_call_free`: replace inline `SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")` load with `from core.embeddings import embed_text; return embed_text(prompt)` — uses worker singleton, not per-call reload
  2. Add `stream_llm(task: str, prompt: str, **kwargs) -> Iterator[str]`: powerful tier only; uses `_anthropic_client().messages.stream(...)`, yields `event.delta.text` for each `text_delta`; raises `ValueError` if task tier ≠ powerful
  3. Add `transcribe_audio(file_bytes: bytes, filename: str) -> str`: calls `_openai_client().audio.transcriptions.create(model="whisper-1", file=(filename, file_bytes))` — not routed through `call_llm` (different input type) but lives here to satisfy SDK-isolation invariant
  4. Wrap `call_llm` with fallback chain: `_call_powerful` → on Exception try `_call_cheap` → on Exception check stale `llm:{task}:{prompt_hash}` Redis cache → on total failure return `"Service temporarily unavailable. Please try again shortly."` — log each fallback at WARN level

- [ ] T003 [P] Update `core/celery_config.py`:
  - Add to `include=` list: `"modules.fraud.tasks"`, `"modules.contracts.tasks"`, `"modules.agent.tasks"`
  - Add to `task_routes`:
    ```python
    "modules.fraud.tasks.run_fraud_check":            {"queue": "nestai:medium"},
    "modules.contracts.tasks.analyze_contract_async": {"queue": "nestai:high"},
    "modules.agent.tasks.index_rag_chunk":            {"queue": "nestai:low"},
    "modules.agent.tasks.seed_rag_embeddings":        {"queue": "nestai:low"},
    ```

**Checkpoint**: `from core.llm_router import stream_llm, transcribe_audio` imports without error inside api container

---

## Phase 3: Self-Contained Modules (no cross-module deps)

**Purpose**: Build area_intel and notifications first — they are depended on by estimator and agent respectively.

### T004 [P] — `modules/area_intel/` (full module)

- `models.py`: `Neighborhood` SQLAlchemy model mapping to existing `neighborhoods` table (id, name, name_ar, city, electricity, generator_cost, internet, transport, safety, student_vibe, lat, lng)
- `schemas.py`: `NeighborhoodOut(BaseModel)` with all 8 score fields; `CompareRequest(BaseModel)`: `{area_a: str, area_b: str}`; `CompareOut(BaseModel)`: `{area_a: NeighborhoodOut, area_b: NeighborhoodOut}`
- `repository.py`: `get_by_name(db, name) -> Neighborhood | None`; `get_by_id(db, id) -> Neighborhood | None`
- `service.py`:
  - `get_by_name(db, redis, name) -> NeighborhoodOut`: check Redis `area:{neighbourhood_id}` Hash (24h TTL) → fallback to repo; write cache on miss; raise 404 if not found
  - `compare(db, redis, area_a, area_b) -> CompareOut`: call `get_by_name` for each; return both
- `router.py`:
  - `GET /areas/{name}` → `svc.get_by_name()`
  - `POST /areas/compare` → `svc.compare()`
- `__init__.py`: empty

### T005 [P] — `modules/notifications/` (full module)

- `models.py`: `Notification` SQLAlchemy model mapping to existing `notifications` table (id, user_id, type, payload JSONB, read, created_at)
- `schemas.py`: `NotificationOut(BaseModel)`: {id, type, payload, read, created_at}
- `repository.py`:
  - `get_unread(db, user_id) -> list[Notification]`
  - `mark_read(db, notification_id, user_id) -> bool` — returns False if not found or wrong owner
  - `get_all(db, user_id, limit=50) -> list[Notification]`
  - `create(db, user_id, type, payload) -> Notification`
- `service.py`:
  - `stream_events(db, redis, user_id) -> AsyncGenerator[str, None]`: flush unread DB notifications as `data: {json}\n\n`; subscribe to `RedisKeys.sse_channel(user_id)` pub/sub; yield each message; unsubscribe on GeneratorExit
  - `get_all(db, user_id) -> list[NotificationOut]`
  - `mark_read(db, user_id, notification_id) -> None`: raise 404 or 403 on failure
  - `publish(redis, user_id, type, payload) -> None`: publish to `sse:{user_id}` channel
- `router.py`:
  - `GET /notifications/stream` → `StreamingResponse(svc.stream_events(), media_type="text/event-stream")`
  - `GET /notifications` → `svc.get_all()`
  - `POST /notifications/{id}/read` → `svc.mark_read()`; status 204
- `__init__.py`: empty

**Checkpoint for T004+T005**: `curl http://localhost:8000/areas/hamra` returns neighbourhood JSON; `curl http://localhost:8000/notifications` returns `[]` for a valid student token

---

## Phase 4: Estimator Module (depends on area_intel)

- [ ] T006 Create `modules/estimator/` (full module):
  - `models.py`: `CostEstimate` SQLAlchemy model mapping to `cost_estimates` table
  - `schemas.py`:
    - `EstimateRequest(BaseModel)`: `{rent: int, neighbourhood_id: int, university_id: int | None}`
    - `EstimateOut(BaseModel)`: `{rent, generator, water, internet, transport, total_monthly, commute_minutes: int | None}`
  - `repository.py`: `save(db, user_id, listing_id, data) -> CostEstimate`
  - `service.py`:
    - `calculate(db, redis, user_id, req: EstimateRequest) -> EstimateOut`:
      1. Call `area_intel.service.get_by_name()` via neighbourhood_id to get `generator_cost` — wait, service takes name not id; use `area_intel.repository` — NO: must use area_intel.service. Use `area_intel.repository.get_by_id(db, neighbourhood_id)` — but estimator can't import area_intel.repository. CORRECT approach: `area_intel.service.get_by_id(db, redis, neighbourhood_id)` — add `get_by_id` method to area_intel.service
      2. Compute: `water = 15`, `internet = 30`, `transport = neighbourhood_transport_score * 10` (rough estimate)
      3. OSRM call if university_id provided: `GET http://osrm:5000/route/v1/driving/{listing_lng},{listing_lat};{uni_lng},{uni_lat}?overview=false` — extract `routes[0].duration / 60`; on any exception set `commute_minutes = None`
      4. `total_monthly = rent + generator + water + internet + transport`
      5. Save to `cost_estimates`
      6. Return `EstimateOut`
  - `router.py`: `POST /estimator/calculate` → bearer(student) → `svc.calculate()`
  - `__init__.py`: empty

  **Note**: Add `get_by_id(db, redis, neighbourhood_id) -> NeighborhoodOut` to `area_intel/service.py` and `get_by_id(db, id)` to `area_intel/repository.py`

**Checkpoint**: `POST /estimator/calculate` with valid neighbourhood_id returns JSON with all 7 fields; commute_minutes is int or null

---

## Phase 5: Housing Module Additions (needed by fraud)

- [ ] T007 Add 4 new methods to `modules/housing/repository.py`:
  - `semantic_search(db, query_embedding: list[float], limit: int, min_price: int | None, max_price: int | None, neighbourhood_id: int | None) -> list[Listing]`: raw SQL using pgvector operator `<=>` (cosine), filters applied as WHERE clauses, only `status = 'active'` rows
  - `get_neighbourhood_stats(db, neighbourhood_id: int) -> dict`: `SELECT AVG(price), STDDEV(price) FROM listings WHERE neighbourhood_id = ? AND status = 'active'` — returns `{median: float, stddev: float}`
  - `get_landlord_listing_count(db, landlord_id: int) -> int`: `SELECT COUNT(*) FROM listings WHERE landlord_id = ?`
  - `get_listing_photo_phashes(db, listing_id: int) -> list[str]`: `SELECT phash FROM listing_photos WHERE listing_id = ? AND phash IS NOT NULL`

- [ ] T008 [P] Add 4 new methods to `modules/housing/service.py`:
  - `async def semantic_search(self, query_embedding, filters, limit=10) -> list[Listing]`: delegates to `self._repo.semantic_search(...)`
  - `async def get_neighbourhood_stats(self, neighbourhood_id) -> dict`: delegates to repo
  - `async def get_landlord_listing_count(self, landlord_id) -> int`: delegates to repo
  - `async def get_listing_photo_phashes(self, listing_id) -> list[str]`: delegates to repo

**Checkpoint**: Import both updated files without error; run `docker compose exec api pytest tests/test_api_listings.py -v` — all pass (regression check)

---

## Phase 6: Fraud Module (depends on housing additions)

- [ ] T009 Create `modules/fraud/` (full module):
  - `models.py`: `FraudReport` SQLAlchemy model mapping to `fraud_reports` table (id, listing_id, score, price_zscore, evidence JSONB, created_at, updated_at)
  - `schemas.py`: `FraudReportOut(BaseModel)`: {listing_id, score, price_zscore, evidence: {price_flags, phone_flags, photo_flags, text_flags}, computed_at}
  - `repository.py`:
    - `get_by_listing(db, listing_id) -> FraudReport | None`
    - `upsert(db, listing_id, score, price_zscore, evidence) -> FraudReport`
  - `service.py`:
    - `get_report(db, redis, listing_id) -> FraudReportOut`:
      1. Check Redis `fraud:{listing_id}` Hash (12h TTL) — return cached if hit
      2. Query `fraud_reports` by listing_id — return if exists
      3. If neither, return a 0-score placeholder (fraud task may still be running)
    - `compute_fraud_score(db, listing_id) -> FraudReportOut` (called from Celery task):
      1. Load listing via `HousingService(db).get_listing(listing_id)` — return None if deleted
      2. **Price z-score**: call `HousingService(db).get_neighbourhood_stats(listing.neighbourhood_id)` → compute z-score `(listing.price - median) / stddev`; if z-score < -2.0 add "price_suspicious" to price_flags; price_component = min(abs(z-score) / 3.0, 1.0)
      3. **Phone dedup**: call `HousingService(db).get_landlord_listing_count(listing.landlord_id)` → if count ≥ 3 add "multiple_listings_same_landlord" to phone_flags; phone_component = min((count - 1) / 5.0, 1.0)
      4. **Photo phash**: call `HousingService(db).get_listing_photo_phashes(listing.listing_id)` → for each phash, compare hamming distance against all other known phashes in `listing_photos` (raw query in fraud.repository); if any distance ≤ 10 add "duplicate_photo_detected" to photo_flags; photo_component = 1.0 if any match else 0.0
      5. **Text flags**: call `call_llm("classify_fraud_text", listing_text)` — qualitative evidence only, appended to text_flags, does NOT affect numeric score
      6. `score = 0.5 * price_component + 0.3 * phone_component + 0.2 * photo_component`
      7. Upsert `fraud_reports`; write to Redis `fraud:{listing_id}` Hash (12h TTL); update `listings.fraud_score`
  - `router.py`: `GET /fraud/{listing_id}` → optional auth → `svc.get_report()`
  - `__init__.py`: empty

  **Note**: fraud.repository needs one additional method: `get_all_phashes_except(db, listing_id) -> list[str]` — queries `listing_photos` for all phash values where listing_id ≠ input. This is cross-table but fraud.repository owns the computation; the raw SQL goes in fraud.repository directly (accessing listing_photos which housing owns). This is the one acceptable exception to boundary rules for a read-only aggregation query — document it explicitly with a comment.

**Checkpoint**: `GET /fraud/1` returns valid JSON with all evidence keys present

---

## Phase 7: Contracts Module

- [ ] T010 Create `modules/contracts/` (full module):
  - `models.py`: `Contract` SQLAlchemy model mapping to `contracts` table (id, user_id, minio_key, ocr_used, analysis JSONB, status, created_at)
  - `schemas.py`:
    - `ContractCreateOut(BaseModel)`: {contract_id, status}
    - `ContractOut(BaseModel)`: {id, ocr_used, status, analysis, created_at}
    - `RiskItem(BaseModel)`: {level: str, clause_text: str, explanation: str}
  - `repository.py`:
    - `create(db, user_id, minio_key) -> Contract`
    - `get_by_id(db, contract_id) -> Contract | None`
    - `update_status(db, contract_id, status: str) -> None`
    - `update_analysis(db, contract_id, ocr_used: bool, analysis: dict) -> None`
  - `service.py`:
    - `upload_and_queue(db, redis, user_id, file: UploadFile) -> ContractCreateOut`:
      1. Validate magic bytes: `%PDF` → raise 400 if not PDF
      2. Validate size: reject > 10MB before reading full content
      3. Upload to MinIO `Bucket.CONTRACTS` via `core.storage.upload_file`
      4. `repo.create(db, user_id, minio_key)` → get contract_id
      5. `analyze_contract_async.delay(contract_id)` → Celery task
      6. Return `{contract_id, status: "pending"}`
    - `get_contract(db, user_id, contract_id) -> ContractOut`: fetch row; raise 403 if user_id mismatch; raise 404 if not found
  - `router.py`:
    - `POST /contracts/analyze` → bearer(student) → `svc.upload_and_queue()`; status 202
    - `GET /contracts/{id}` → bearer(student, own) → `svc.get_contract()`
  - `__init__.py`: empty

**Checkpoint**: `POST /contracts/analyze` with a valid PDF returns `{contract_id, status: "pending"}`; `GET /contracts/{id}` returns the row

---

## Phase 8: Agent Module (depends on all other modules)

Agent is built in sub-steps: models/schemas → repository → tools → graph → service → router.

- [ ] T011 Create `modules/agent/models.py` + `modules/agent/schemas.py`:
  - `models.py`: `AgentSession` (→ agent_sessions), `StudentMemory` (→ student_memory), `RAGChunk` (→ rag_chunks)
  - `schemas.py`:
    - `AgentState(TypedDict)`: {query, session_id, intent, listings, retry_count, comparison, response, errors}
    - `ChatRequest(BaseModel)`: {query: str, session_id: str | None}
    - `ChatResponse(BaseModel)`: {response: str, session_id: str}
    - `TranscribeResponse(BaseModel)`: {text: str}

- [ ] T012 Create `modules/agent/repository.py`:
  - `create_session(db, user_id, session_id) -> AgentSession`
  - `update_session(db, session_id, history: list, summary: str) -> None`
  - `get_session(db, session_id) -> AgentSession | None`
  - `listing_exists(db, listing_id: int) -> bool`: `SELECT EXISTS(SELECT 1 FROM listings WHERE id = ?)` — agent owns this query for validation
  - `search_rag_chunks(db, embedding: list[float], limit=3) -> list[dict]`: pgvector cosine search on `rag_chunks.embedding` WHERE `source_type = 'housing_faq'`; returns top 3 `{chunk_text, source_type, language}`
  - `upsert_student_memory(db, user_id, preferred_areas, liked_count) -> StudentMemory`

- [ ] T013 Create `modules/agent/tools.py` — 9 MCP tool functions:
  ```
  search_listings(db, embedding, filters) -> list[dict]
    → housing.service.semantic_search(embedding, filters)

  calculate_commute(listing_lat, listing_lng, uni_lat, uni_lng) -> dict
    → HTTP GET osrm:5000/route/v1/driving/...
    → on any error: return {"commute_minutes": null, "note": "Commute data temporarily unavailable"}

  get_area_scores(db, redis, area_name) -> dict
    → area_intel.service.get_by_name(db, redis, area_name)

  check_fraud(db, redis, listing_id) -> dict
    → fraud.service.get_report(db, redis, listing_id)

  get_roommate_matches(db, user_id) -> list[dict]
    → roommate.service.get_matches(db, user_id)

  estimate_cost(db, redis, rent, neighbourhood_id, university_id) -> dict
    → estimator.service.calculate(db, redis, user_id=None, req=...)

  compare_areas(db, redis, area_a, area_b) -> dict
    → area_intel.service.compare(db, redis, area_a, area_b)

  transcribe_audio(file_bytes, filename) -> str
    → llm_router.transcribe_audio(file_bytes, filename)

  survival_search(db, query_text) -> list[dict]
    → embed query: core.embeddings.embed_text(query_text)
    → agent.repository.search_rag_chunks(db, embedding, limit=3)
  ```
  All tool functions are plain Python functions (not Celery tasks). They are called synchronously from graph nodes.

- [ ] T014 Create `modules/agent/graph.py` — LangGraph StateGraph:
  ```python
  from langgraph.graph import StateGraph, END
  from modules.agent.schemas import AgentState

  def build_graph(db, redis) -> CompiledGraph:
      graph = StateGraph(AgentState)
      graph.add_node("parse_intent",         parse_intent_node(db, redis))
      graph.add_node("search_and_rank",      search_and_rank_node(db, redis))
      graph.add_node("validate_results",     validate_results_node())
      graph.add_node("compare",              compare_node(db, redis))
      graph.add_node("validate_comparison",  validate_comparison_node(db))
      graph.add_node("explain_and_respond",  explain_and_respond_node(db, redis))

      graph.set_entry_point("parse_intent")
      graph.add_edge("parse_intent", "search_and_rank")
      graph.add_edge("search_and_rank", "validate_results")
      graph.add_conditional_edges(
          "validate_results",
          lambda s: "search_and_rank" if s["retry_count"] < 2 and not s["listings"] else "compare"
      )
      graph.add_edge("compare", "validate_comparison")
      graph.add_conditional_edges(
          "validate_comparison",
          lambda s: "compare" if s.get("_regen") else "explain_and_respond"
      )
      graph.add_edge("explain_and_respond", END)
      return graph.compile()
  ```
  Each node function is defined in graph.py using closures that capture db/redis. Node implementations:
  - `parse_intent_node`: sanitize query via `core.security.sanitize_prompt(query)`; `call_llm("parse_intent", sanitized)` → JSON intent; update state
  - `search_and_rank_node`: call search_listings + calculate_commute + get_area_scores + check_fraud tools; assemble listings list; update state
  - `validate_results_node`: if listings empty and retry_count < 2: increment retry_count, widen filters (expand max_price by 20%, expand area to adjacent); else pass through
  - `compare_node`: if no listings, set response to "no matches" message and skip; else sanitize listings context; `call_llm("agent_compare_explain", context)` → comparison string
  - `validate_comparison_node`: parse listing IDs cited in comparison; for each: `agent.repository.listing_exists(db, id)`; if any missing, set `_regen=True` in state; else clear `_regen`
  - `explain_and_respond_node`: streams via `stream_llm("agent_compare_explain", final_prompt)` (yields to caller); persist state to Redis; at end call `call_llm("summarize_session", history_text)` for PostgreSQL summary; write `agent_sessions` row

- [ ] T015 Create `modules/agent/service.py`:
  - `class AgentService`:
    - `__init__(self, db, redis)`
    - `async def chat(self, user_id, req: ChatRequest) -> AsyncGenerator[str, None]`:
      1. Load or create session_id (generate UUID if req.session_id is None)
      2. Load session state from Redis `session:{user_id}:{session_id}` (JSON); initialize if new
      3. Build graph: `graph = build_graph(self.db, self.redis)`
      4. Run graph via `graph.stream(state)` — this yields state updates per node
      5. For the final node's response, yield token-level SSE via `stream_llm` (implemented inside graph.py's `explain_and_respond_node`)
      6. Yield `data: [DONE]\n\n`
    - `async def transcribe(self, file: UploadFile) -> str`:
      1. Validate file size ≤ 25MB; validate extension in {.webm, .mp4, .wav, .m4a}
      2. Read bytes; call `llm_router.transcribe_audio(file_bytes, file.filename)`
      3. Return transcription text

- [ ] T016 Create `modules/agent/router.py`:
  - `POST /agent/chat` → bearer(student) → `StreamingResponse(svc.chat(user_id, req), media_type="text/event-stream")`
  - `POST /agent/transcribe` → bearer(student) → `svc.transcribe(file)` → `TranscribeResponse`

**Checkpoint**: `POST /agent/chat` with `{"query": "2 bedroom in Hamra", "session_id": null}` streams SSE tokens ending with `[DONE]`

---

## Phase 9: Celery Tasks

- [ ] T017 [P] Create `modules/fraud/tasks.py`:
  ```python
  from core.celery_config import celery_app
  from fraud.service import FraudService

  @celery_app.task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
  def run_fraud_check(listing_id: int):
      with SyncSessionLocal() as db:
          FraudService(db, get_sync_redis()).compute_fraud_score(db, listing_id)
  ```

- [ ] T018 [P] Create `modules/contracts/tasks.py`:
  - `analyze_contract_async(contract_id: int)` Celery task on `nestai:high`:
    1. Load contract from DB; set status → "ocr_running" if needed, else "analyzing"
    2. Download PDF bytes from MinIO via `core.storage.download_file(minio_key)`
    3. Try PyMuPDF (`fitz.open(stream=bytes)`) → extract text from all pages
    4. If text.strip() == "": set `ocr_used = True`; convert pages to images; `call_llm("ocr_analyze_contract", images_prompt)` (GPT-4o Vision)
    5. Else: `call_llm("analyze_contract", text_prompt)` (Claude Sonnet)
    6. Parse JSON response → list of RiskItems sorted high → medium → low
    7. `repo.update_analysis(db, contract_id, ocr_used, analysis)`; set status → "complete"
    8. On exception: set status → "failed"; log ERROR
    - `autoretry_for=(Exception,)`, `max_retries=2`, `retry_backoff=True`

- [ ] T019 [P] Create `modules/agent/tasks.py`:
  - `index_rag_chunk(chunk_id: int)` on `nestai:low`:
    - Load chunk text from DB; embed via `embed_text(chunk_text)`; update `rag_chunks.embedding`
    - `autoretry_for=(Exception,)`, `max_retries=3`, `retry_backoff=True`
  - `seed_rag_embeddings()` on `nestai:low`:
    - Query all `rag_chunks WHERE embedding IS NULL`; call `index_rag_chunk.delay(id)` for each

- [ ] T020 Update `modules/housing/service.py` to trigger fraud check after listing creation:
  - In `create_listing()`, after `embed_listing.delay(listing.id)`, add:
    ```python
    from modules.fraud.tasks import run_fraud_check
    run_fraud_check.delay(listing.id)
    ```

**Checkpoint**: Create a listing → `docker compose logs worker-medium --tail=20` shows `run_fraud_check` task received and completed

---

## Phase 10: Register Routers + Run Seeds

- [ ] T021 Update `app/main.py` — add 6 new router imports and `include_router` calls:
  ```python
  from modules.agent.router       import router as agent_router
  from modules.fraud.router       import router as fraud_router
  from modules.contracts.router   import router as contracts_router
  from modules.area_intel.router  import router as area_intel_router
  from modules.estimator.router   import router as estimator_router
  from modules.notifications.router import router as notifications_router

  app.include_router(agent_router)
  app.include_router(fraud_router)
  app.include_router(contracts_router)
  app.include_router(area_intel_router)
  app.include_router(estimator_router)
  app.include_router(notifications_router)
  ```

- [ ] T022 [P] Seed rag_chunk data and trigger embedding:
  ```bash
  docker compose exec db psql -U nestai -d nestai -f /seed/rag_chunks.sql
  docker compose exec worker-low python -c "from modules.agent.tasks import seed_rag_embeddings; seed_rag_embeddings.delay()"
  ```

**Checkpoint**: `curl http://localhost:8000/health` returns 200; `curl http://localhost:8000/areas/hamra` returns neighbourhood JSON

---

## Phase 11: Tests

- [ ] T023 [P] Create `tests/test_agent_flow.py` (6 tests):
  - `test_parse_intent_extracts_fields`: POST /agent/chat "2-bedroom in Hamra under 700 USD" → response contains Hamra and budget mention
  - `test_validate_results_retries_on_empty`: query with no possible matches (price 1 USD) → response is graceful "no matches" message, not a 500
  - `test_validate_comparison_rejects_hallucinated_id`: mock compare node to return fake listing_id → verify validate_comparison triggers regeneration
  - `test_full_conversation_persisted`: run full graph → `SELECT * FROM agent_sessions WHERE user_id = ?` returns row with non-empty history and summary
  - `test_survival_search_returns_chunks`: POST /agent/chat "generator companies in Hamra" → response references FAQ content (contains "generator" related text)
  - `test_osrm_unavailable_graceful`: set OSRM_URL to unreachable host → POST /agent/chat returns 200 with response that contains commute as "—" or "unavailable", no 500

- [ ] T024 [P] Create `tests/test_fraud.py` (5 tests):
  - `test_price_zscore_flag`: insert listing at price far below neighbourhood median → GET /fraud/{id} → score > 0.3 and price_flags non-empty
  - `test_phone_dedup_flag`: same landlord creates 3 listings → run_fraud_check on 4th → phone_flags non-empty
  - `test_photo_phash_flag`: insert two listing_photos with near-identical phash (hamming ≤ 10) → photo_flags non-empty after fraud check
  - `test_fraud_cache_hit`: GET /fraud/{id} twice → verify Redis key `fraud:{id}` exists with TTL ≈ 12h
  - `test_score_formula_weights`: stub all three components at known values → assert `score == 0.5*p + 0.3*ph + 0.2*photo` exactly

- [ ] T025 [P] Create `tests/test_contracts.py` (4 tests):
  - `test_text_pdf_analysis`: upload `tests/fixtures/sample_contract.pdf` (text PDF with a known clause) → wait for Celery → GET /contracts/{id} → risk_items contains ≥ 1 high item with all 3 fields
  - `test_scanned_pdf_ocr_fallback`: upload `tests/fixtures/scanned_contract.pdf` (image-only PDF) → GET /contracts/{id} → ocr_used=true, risk_items present
  - `test_pdf_too_large_rejected`: upload a file > 10MB → 400 response, no row in contracts table
  - `test_password_protected_pdf`: upload `tests/fixtures/protected.pdf` → 400 response within 5s

  **Note**: Add test fixture PDFs to `tests/fixtures/` (sample_contract.pdf, scanned_contract.pdf, protected.pdf)

**Checkpoint**: 
```bash
docker compose exec api pytest tests/test_agent_flow.py -v
docker compose exec api pytest tests/test_fraud.py -v
docker compose exec api pytest tests/test_contracts.py -v
```
All pass.

---

## Phase 12: Spec Validation + Regression

- [ ] T026 [P] Run spec-validator: `docker compose --profile spec run spec-validator` — must exit 0
- [ ] T027 [P] Run Phase 1 regression: `docker compose exec api pytest tests/test_api_listings.py -v` — all pass (verify housing.service changes introduced no regressions)
- [ ] T028 [P] Run Phase 2a regression: `docker compose exec api pytest tests/test_embeddings.py -v` — all pass

---

## Dependency Graph

```
T001 (seed SQL)
     │
     ├─T002, T003 [parallel — core updates]
     │
     ├─T004, T005 [parallel — area_intel, notifications]
     │       │
     │       └─T006 (estimator — needs area_intel)
     │
     ├─T007, T008 [parallel — housing additions]
     │       │
     │       └─T009 (fraud — needs housing additions)
     │
     ├─T010 (contracts — standalone)
     │
     └─ all above done ─→ T011→T012→T013→T014→T015→T016 (agent — sequential)
                                    │
                           T017, T018, T019 [parallel — Celery tasks]
                                    │
                                   T020 (housing fraud trigger)
                                    │
                                   T021 (register routers)
                                    │
                                   T022 (seed rag + router check)
                                    │
                          T023, T024, T025 [parallel — tests]
                                    │
                          T026, T027, T028 [parallel — validation]
```

---

## Parallel Opportunities

```bash
# Start immediately in parallel:
T002  # llm_router.py
T003  # celery_config.py
T004  # area_intel module
T005  # notifications module

# After area_intel:
T006  # estimator module

# After T004+T005+T006:
T007  # housing/repository.py additions
T008  # housing/service.py additions

# After housing additions:
T009  # fraud module
T010  # contracts module (can run parallel with T009)

# After all modules (T004-T010):
T011 → T012 → T013 → T014 → T015 → T016  # agent (sequential)

# After service files exist:
T017, T018, T019  # Celery tasks (parallel)
```

---

**Final gate**: `docker compose --profile spec run spec-validator && docker compose exec api pytest tests/ -v`
