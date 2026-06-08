# Tasks: Phase 2a — Embeddings + Roommate Matching

**Input**: specs/002a-embeddings-roommate/ (plan.md, spec.md, data-model.md, research.md, contracts/)

**3 User Stories** | **P1: US1 (listing embeddings), US2 (profile embeddings)** | **P2: US3 (roommate matching)**

---

## Phase 1: Setup (Migration + Worker Config)

**Purpose**: DB schema changes and Celery wiring that block all user story work.

- [ ] T001 Create `migrations/002a_add_profile_dim_vectors.sql` — `ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS dim_sleep/study/cleanliness/guests/budget vector(1024)` + 5 HNSW indexes
- [ ] T002 Apply migration: `docker compose exec db psql -U nestai -d nestai -f /migrations/002a_add_profile_dim_vectors.sql`
- [ ] T003 [P] Add `embed_cache` and `embed_lock` key methods to `core/redis.py` `RedisKeys` class
- [ ] T004 [P] Update `core/celery_config.py` to include `modules.housing.tasks` and `modules.users.tasks` in `include=` list and register `batch_embed_seed_data` beat task (nightly, `nestai:low`)

**Checkpoint**: Migration applied — `\d student_profiles` shows 5 `dim_*` columns. Celery app imports tasks without error.

---

## Phase 2: Foundational — BGE-M3 Core (Blocks US1 + US2)

**Purpose**: Replace the `core/embeddings.py` stub with the full BGE-M3 implementation. Both embedding task modules depend on this.

- [ ] T005 Implement `core/embeddings.py` — full BGE-M3 replacement:
  - Module-level `_model = None`
  - `_load_model()`: `SentenceTransformer("BAAI/bge-m3")`, sets `_model`, logs `"BGE-M3 model loaded"` at INFO
  - `worker_process_init` signal: calls `_load_model()` once at worker startup
  - `embed_text(text, normalize=True) -> list[float]`: calls `_model.encode()`, asserts `len(vec) == 1024`, returns list
  - `embed_batch(texts, normalize=True) -> list[list[float]]`: batch encode, assert each 1024-dim
  - Redis cache check/write in both functions using `RedisKeys.embed_cache(sha256(text)[:16])`, 48h TTL
  - Raises `NotImplementedError` if `_model is None` (worker not initialised yet)

**Checkpoint**: `from core.embeddings import embed_text; embed_text("test")` works inside `worker-low` container. Logs show exactly one `"BGE-M3 model loaded"` line per worker process.

---

## Phase 3: User Story 1 — Listings Embedded Automatically (P1)

**Goal**: Every listing create/update triggers a background BGE-M3 embed. `listings.embedding` is never stale.

**Independent Test**: POST listing → wait 5s → `SELECT embedding IS NOT NULL FROM listings WHERE id = ?` returns `t`.

- [ ] T006 [US1] Create `modules/housing/tasks.py`:
  - `embed_listing(listing_id)` Celery task on queue `nestai:low`:
    - Acquire Redis lock `RedisKeys.embed_lock(listing_id)` (SET NX, 30s TTL) — skip if locked
    - Load listing via `HousingRepository(db).get_by_id(listing_id)` — return cleanly if None (deleted)
    - Fetch neighbourhood name via raw SQL or join
    - Build text: `"{title}. {description}. Neighbourhood: {neighbourhood_name}. Amenities: {amenity_keys_joined}"`
    - Call `embed_text(text)` → 1024-dim vector
    - Write vector: `await repo.update_embedding(listing_id, vector)`
    - `autoretry_for=(Exception,)`, `max_retries=3`, `retry_backoff=True`
  - `batch_embed_seed_data()` Celery task on queue `nestai:low`:
    - Query all listings where `embedding IS NULL`
    - Call `embed_listing.delay(id)` for each

- [ ] T007 [US1] Add `update_embedding(listing_id, vector)` method to `modules/housing/repository.py`

- [ ] T008 [US1] Update `modules/housing/service.py`:
  - `create_listing()`: after `await self._repo.create(...)`, call `embed_listing.delay(listing.id)`
  - `update_listing()`: after `await self._repo.update(...)`, call `embed_listing.delay(listing_id)`

**Checkpoint**: Create listing → 5s → `embedding IS NOT NULL`. Update listing → `embed_listing` task queued again (visible in Flower at localhost:5555).

---

## Phase 4: User Story 2 — Student Profile Embedded After Onboarding (P1)

**Goal**: `POST /users/onboarding` triggers `embed_profile` task that writes all 6 vectors (`embedding` + 5 `dim_*`) to `student_profiles`.

**Independent Test**: POST onboarding → wait 10s → all 6 columns non-null for that user.

- [ ] T009 [US2] Create `modules/users/tasks.py`:
  - `embed_profile(user_id)` Celery task on queue `nestai:low`:
    - Load profile via `UsersRepository(db).get_profile(user_id)` — return if None
    - Build full-profile text: concatenate all 8 preference fields as natural language
    - Build 5 dimension texts using template from data-model.md; use `"unspecified"` for null fields
    - Call `embed_batch([full_text, sleep_text, study_text, clean_text, guests_text, budget_text])`
    - Write all 6 vectors: `await repo.update_profile_embeddings(user_id, embedding, dim_sleep, ...)`
    - `autoretry_for=(Exception,)`, `max_retries=3`, `retry_backoff=True`
  - `update_preference_vector(user_id)` Celery task on queue `nestai:medium`:
    - Same as `embed_profile` but only re-embeds changed dimensions
    - Updates `preference_vector` column too

- [ ] T010 [US2] Add `update_profile_embeddings(user_id, embedding, dim_sleep, dim_study, dim_cleanliness, dim_guests, dim_budget)` to `modules/users/repository.py`

- [ ] T011 [US2] Update `modules/users/service.py` `save_onboarding()`:
  - After saving profile, call `embed_profile.delay(user_id)`

**Checkpoint**: POST /users/onboarding → wait 10s → `SELECT embedding IS NOT NULL, dim_sleep IS NOT NULL, dim_study IS NOT NULL, dim_cleanliness IS NOT NULL, dim_guests IS NOT NULL, dim_budget IS NOT NULL FROM student_profiles WHERE user_id = ?` — all `t`.

---

## Phase 5: User Story 3 — Roommate Matching with 5-Dimension Scores (P2)

**Goal**: `GET /roommate/matches` returns ranked candidates with per-dimension cosine similarity scores. `POST /roommate/requests` persists a request.

**Independent Test**: Jawad (night_owl) vs Omar (early_bird) → `dimensions.sleep < 0.4`.

- [ ] T012 [P] [US3] Create `modules/roommate/models.py` — `RoommateRequest` SQLAlchemy ORM model mapping to existing `roommate_requests` table

- [ ] T013 [P] [US3] Create `modules/roommate/schemas.py`:
  - `DimensionScores(BaseModel)`: `sleep, study, cleanliness, guests, budget` (all `float`)
  - `MatchOut(BaseModel)`: `user_id: int`, `score: float`, `dimensions: DimensionScores`
  - `RequestCreate(BaseModel)`: `to_user_id: int`
  - `RequestOut(BaseModel)`: `id, from_user_id, to_user_id, score, dimensions, status, created_at`

- [ ] T014 [US3] Create `modules/roommate/repository.py`:
  - `get_matches(db, caller_profile) -> list[dict]`: executes the 5-operator cosine SQL from research.md using the caller's 5 `dim_*` vectors as bind parameters; returns up to 20 rows ordered by average score desc; skips rows where `dim_sleep IS NULL`
  - `create_request(db, from_user_id, to_user_id, score, dimensions) -> RoommateRequest`: inserts into `roommate_requests`; handles duplicate gracefully

- [ ] T015 [US3] Create `modules/roommate/service.py`:
  - `get_matches(db, current_user_id) -> list[MatchOut]`: load caller's profile; raise 422 if `dim_sleep IS NULL`; call repo `get_matches()`; map rows to `MatchOut`
  - `send_request(db, from_user_id, to_user_id) -> RequestOut`: validate target user exists and is a student; call repo `create_request()`

- [ ] T016 [US3] Create `modules/roommate/router.py`:
  - `GET /roommate/matches` → `require_student_role` → `svc.get_matches()`
  - `POST /roommate/requests` → `require_student_role` → `svc.send_request()`

- [ ] T017 [US3] Create `modules/roommate/__init__.py` (empty)

- [ ] T018 [US3] Register roommate router in `app/main.py`: `from modules.roommate.router import router as roommate_router` + `app.include_router(roommate_router)`

- [ ] T019 [US3] Update `specs/all_modules.yaml` — add `roommate` module endpoints (`GET /roommate/matches`, `POST /roommate/requests`) with correct auth and response schemas

**Checkpoint**: `GET /roommate/matches` returns JSON array. Jawad–Omar `dimensions.sleep < 0.4`. `POST /roommate/requests` returns 201 with `status: pending`.

---

## Phase 6: Tests

**Goal**: All SC-001 acceptance criteria verified programmatically.

- [ ] T020 Create `tests/test_embeddings.py` with the following test cases:
  - `test_embed_text_dimension`: `embed_text("test")` returns list of length 1024
  - `test_embed_text_normalized`: cosine similarity of a vector with itself ≈ 1.0
  - `test_embed_batch_efficiency`: `embed_batch(["a","b","c"])` returns 3 vectors, all 1024-dim
  - `test_profile_all_6_vectors_populated`: POST onboarding → wait → assert all 6 columns non-null
  - `test_listing_embedding_on_create`: POST listing → wait → `embedding IS NOT NULL`
  - `test_listing_embedding_on_update`: PUT listing → new embed task queued
  - `test_roommate_match_5_dimensions`: GET /roommate/matches → all 5 dimension keys present, values in [0,1]
  - `test_opposite_sleep_low_score`: Jawad vs Omar → `dimensions.sleep < 0.4`
  - `test_no_embedding_returns_422`: new student without onboarding → GET /roommate/matches → 422

**Checkpoint**: `docker compose exec api pytest tests/test_embeddings.py -v` — all 9 tests pass.

---

## Phase 7: Polish & Spec Validation

- [ ] T021 [P] Run spec validator: `docker compose --profile spec run spec-validator` — must exit 0
- [ ] T022 [P] Run Phase 1 regression: `docker compose exec api pytest tests/test_api_listings.py -v` — all pass (no regressions from service.py changes)
- [ ] T023 [P] Verify BGE-M3 loads once: `docker compose logs worker-low | grep "BGE-M3"` — exactly 1 line per worker process
- [ ] T024 [P] Trigger batch seed embed: `embed_listing.delay()` for all 50 seed listings — verify `COUNT(*) WHERE embedding IS NOT NULL = 50`

---

## Dependencies & Execution Order

```
T001→T002 (migration applied)
     ↓
T003, T004 [parallel]
     ↓
T005 (BGE-M3 core — blocks T006, T009)
     ↓
┌────────────────────┬──────────────────────┐
│  US1 (T006→T008)  │   US2 (T009→T011)   │
└────────────────────┴──────────────────────┘
                     ↓ (both complete)
         US3 (T012,T013 parallel → T014→T015→T016→T017→T018→T019)
                     ↓
              Tests (T020)
                     ↓
              Polish (T021–T024 parallel)
```

---

## Parallel Opportunities

```bash
# Phase 1 — run together:
T003  # redis.py key methods
T004  # celery_config.py update

# Phase 5 — run together:
T012  # roommate/models.py
T013  # roommate/schemas.py

# Phase 7 — run together:
T021  # spec-validator
T022  # regression test suite
T023  # BGE-M3 load verification
T024  # batch seed embed
```

---

## Implementation Strategy

### MVP (US1 + US2 only — embeddings working)
1. T001 → T005 (setup + BGE-M3 core)
2. T006 → T008 (US1 listing embeddings)
3. T009 → T011 (US2 profile embeddings)
4. Validate: all seed listings embedded, Jawad's profile has 6 vectors

### Full (add US3 — roommate matching)
5. T012 → T019 (roommate module)
6. T020 (tests)
7. T021 → T024 (polish + validation)
