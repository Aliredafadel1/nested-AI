# Feature Specification: Phase 2a — Embeddings + Roommate Matching

**Feature Branch**: `002a-embeddings-roommate`

**Created**: 2026-06-05

**Status**: Draft

**Scope**: Day 4. MiniLM embedding pipeline, listing embeddings, student profile embeddings, roommate compatibility engine. Requires Phase 1 complete.

---

## Clarifications

### Session 2026-06-06

- Q: How are the 5 roommate dimension scores derived from embeddings? → A: Option C — 5 separate MiniLM sub-embeddings per student, one per dimension field group (sleep, study, cleanliness, guests, budget). Each sub-embedding is a `vector(384)` stored as a dedicated column in `student_profiles`. Dimension score = cosine similarity between the two students' matching sub-embedding vectors.
- Q: When a listing is updated via `PUT /listings/{id}`, should its embedding be refreshed? → A: Option A — re-embed on every `PUT` regardless of which fields changed. `housing/service.py` queues a new `embed_listing` Celery task after every successful update.
- Q: How are MiniLM model weights sourced? → A: Option A — auto-download from HuggingFace Hub (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) on first `worker_process_init`, cached to a named Docker volume (`bge_model_cache`) so subsequent restarts are instant. Production image (Phase 4) may bake weights in for offline demo reliability.
- Q: What is the retry policy for failed embed tasks? → A: Option A — Celery autoretry, 3 attempts, exponential backoff (10s → 30s → 90s). After 3 failures, log error and leave `embedding = NULL`; the nightly `batch_embed_seed_data` beat task acts as the safety net to recover any nulls.
- Q: Which listing fields are concatenated as MiniLM input text? → A: Option B — `"{title}. {description}. Neighbourhood: {neighbourhood_name}. Amenities: {amenities_keys_joined}"`. Numeric fields (price, bedrooms) are excluded — handled by SQL filters, not semantic search.

### Session 2026-07-20

- Q: A full-system test found the shipped implementation (`core/embeddings.py`, `migrations/init.sql`) has always used `paraphrase-multilingual-MiniLM-L12-v2` (384-dim), not BGE-M3 (1024-dim) as this spec originally documented. Which do we align on? → A: Keep MiniLM-384 — it's already what's running, already seeded, and already covered by `test_embeddings.py`. This spec and the constitution (`.specify/memory/constitution.md`, v1.1.0) were amended to document the model actually in use rather than force a re-embed migration to match the original (aspirational) BGE-M3 choice.

---

## User Scenarios & Testing

### User Story 1 — Listings Are Embedded Automatically After Creation (Priority: P1)

When a landlord posts a listing (Phase 1), a Celery task embeds it in the background using MiniLM. The 384-dim vector is stored in `listings.embedding`. The student never waits for this — it happens asynchronously.

**Why this priority**: Embeddings power the agent's semantic search (Phase 2b) and roommate matching. They must exist before those features work.

**Independent Test**: Post a listing → wait for `embed_listing` Celery task → verify `listings.embedding` is a 384-dim vector and is not null.

**Acceptance Scenarios**:

1. **Given** a new listing is created, **When** the `embed_listing` Celery task runs on `nestai:low`, **Then** `listings.embedding` is populated with a non-null `vector(384)`.
2. **Given** MiniLM is already loaded at worker startup, **When** `embed_listing` is called, **Then** the model is NOT reloaded — it reuses the worker-level instance.
3. **Given** two listings are created simultaneously, **When** the distributed lock `lock:embed:{listing_id}` is checked, **Then** only one embed task runs per listing (no duplicate vectors).

---

### User Story 2 — Student Profile Is Embedded After Onboarding (Priority: P1)

After the student completes the 8-question onboarding (Phase 3 UI, but the API is built here), their preferences are embedded into a 384-dim `student_profiles.embedding` vector (full-profile) **and** 5 per-dimension sub-embedding vectors. These vectors power roommate matching.

**Why this priority**: Roommate matching (User Story 3) depends on all 6 vectors existing.

**Independent Test**: `POST /users/onboarding` with preference data → `student_profiles.embedding` and all 5 `dim_*` columns are populated.

**Acceptance Scenarios**:

1. **Given** a student submits onboarding data, **When** the `embed_profile` Celery task runs, **Then** `student_profiles.embedding` and all 5 dimension vectors (`dim_sleep`, `dim_study`, `dim_cleanliness`, `dim_guests`, `dim_budget`) are non-null `vector(384)`.
2. **Given** a student updates a preference, **When** `update_preference_vector` Celery task runs on `nestai:medium`, **Then** `student_profiles.preference_vector` and the affected `dim_*` column are updated within 5 minutes.

---

### User Story 3 — Roommate Matching Returns 5-Dimension Scores (Priority: P2)

A student calls `GET /roommate/matches`. For each candidate student, the engine runs 5 pgvector cosine similarity queries — one per sub-embedding column — to produce independent dimension scores. Results are ranked by average total score.

**Dimension → field group mapping:**

| Dimension | Text fed to MiniLM |
|---|---|
| sleep | `"sleep schedule: {sleep_schedule}"` |
| study | `"study habits: {study_habits}"` |
| cleanliness | `"cleanliness preference: {cleanliness}"` |
| guests | `"guests policy: {guests}"` |
| budget | `"budget: {budget_min}–{budget_max} USD/month"` |

**Why this priority**: A single total score is not actionable — students need to see dimension-level trade-offs.

**Independent Test**: Two profiles with opposite sleep schedules → `sleep` dimension score < 0.4 and overall match is ranked lower than a compatible pair.

**Acceptance Scenarios**:

1. **Given** two student profiles with all 5 sub-embeddings, **When** `GET /roommate/matches` is called, **Then** the response contains `score` (0–1, average of 5 dimension cosines) and `dimensions: { sleep, study, cleanliness, guests, budget }` (each 0–1).
2. **Given** a student with no embedding yet, **When** `GET /roommate/matches` is called, **Then** a 422 is returned with a message to complete onboarding first.
3. **Given** a student sends a roommate request, **When** `POST /roommate/requests` is called, **Then** `roommate_requests` row is created with `status: pending`.

---

### Edge Cases

- MiniLM worker hasn't initialized yet when the first embed task arrives.
- A listing is deleted before the embed task runs — task should exit cleanly, not error.
- Student profile has null values in some preference fields — sub-embedding for that dimension uses a fallback string (e.g. `"unspecified"`) so embedding still succeeds and all 5 `dim_*` columns are populated.
- pgvector HNSW index does not yet exist — migrations must create it before embed tasks run.

---

## Requirements

- **FR-001**: MiniLM MUST load once via Celery `worker_process_init` signal in `core/embeddings.py`. Never per-request, never per-task invocation.
- **FR-002**: All embeddings MUST be exactly 384 dimensions. Any mismatch MUST raise immediately, not silently truncate.
- **FR-003**: `embed_listing` MUST use the distributed lock `lock:embed:{listing_id}` (30s TTL) to prevent duplicate embeds.
- **FR-004**: Embedding results MUST be cached in Redis (`embed:{text_hash}`, 48h TTL) to avoid redundant MiniLM calls for identical text.
- **FR-005**: `nestai:low` queue MUST be used for embedding tasks (1 worker, 1GB memory cap — comfortably covers MiniLM plus request overhead).
- **FR-006**: Roommate dimension scores MUST be computed via 5 separate pgvector cosine similarity queries (one per `dim_*` column), not in Python application memory.
- **FR-007**: `embed_profile` Celery task MUST produce 6 vectors per student: 1 full-profile embedding (`student_profiles.embedding`) + 5 dimension sub-embeddings (`dim_sleep`, `dim_study`, `dim_cleanliness`, `dim_guests`, `dim_budget`), all `vector(384)`. Each `dim_*` column needs a corresponding HNSW index.
- **FR-008**: Null preference fields MUST use the fallback string `"unspecified"` as MiniLM input for that dimension — never skip or NULL a `dim_*` column after onboarding.
- **FR-009**: Every successful `PUT /listings/{id}` MUST enqueue a new `embed_listing` Celery task to refresh the listing's embedding, regardless of which fields changed.
- **FR-010**: `embed_listing` and `embed_profile` Celery tasks MUST use `autoretry_for=(Exception,)` with `max_retries=3` and `retry_backoff=True` (10s → 30s → 90s). After all retries exhausted, the failure MUST be logged at ERROR level and `embedding` left NULL — no silent swallowing.
- **FR-011**: The text fed to MiniLM for a listing MUST follow the template: `"{title}. {description}. Neighbourhood: {neighbourhood_name}. Amenities: {amenities_keys_joined}"`. Price, bedrooms, and address are excluded from the embedding input.

## Success Criteria

- **SC-001**: `pytest tests/test_embeddings.py -v` — dimension (384), normalize, batch efficiency, all 6 profile vector fields populated tests all pass.
- **SC-002**: `listings.embedding` is populated for all 50 seed listings after `batch_embed_seed_data` Celery task runs.
- **SC-003**: `GET /roommate/matches` returns results with all 5 dimension keys present and each value in [0, 1].
- **SC-004**: MiniLM model is loaded exactly once per worker process (verified via worker startup log).
- **SC-005**: Two students with opposite `sleep_schedule` values produce a `dimensions.sleep` score below 0.4.

## Assumptions

- Phase 1 is complete — listings and student profiles exist in the DB.
- MiniLM weights auto-download from HuggingFace Hub (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) on first worker startup; cached to the `bge_model_cache` Docker volume. Requires internet access on first run.
- pgvector HNSW index exists on `listings.embedding` and `student_profiles.embedding` (created in Phase 1 migrations).
- `student_profiles` table requires 5 additional `vector(384)` columns (`dim_sleep`, `dim_study`, `dim_cleanliness`, `dim_guests`, `dim_budget`) added via migration in this phase.
