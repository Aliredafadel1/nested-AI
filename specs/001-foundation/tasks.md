# Tasks: Phase 1 — Foundation

## Phase 1: Infrastructure

- [ ] T001 Create `Dockerfile` (python:3.11-slim, uvicorn entrypoint)
- [ ] T002 [P] Create `docker/docker-compose.yml` (13 services)
- [ ] T003 [P] Create `.env.dev` (all required vars)
- [ ] T004 [P] Create `requirements.txt`
- [ ] T005 [P] Create `.gitignore`

**Checkpoint**: `docker compose -f docker/docker-compose.yml up -d` — all services healthy

---

## Phase 2: Database

- [ ] T006 Create `migrations/init.sql` (18 tables + HNSW indexes + pg_trgm + seed unis + neighbourhoods)
- [ ] T007 [P] Create `seed/listings.sql` (50 realistic Lebanese listings)

**Checkpoint**: `docker compose exec db psql -U nestai -d nestai -f /migrations/init.sql` — exits 0

---

## Phase 3: Core Infrastructure

- [ ] T008 Create `core/config.py` (Pydantic Settings)
- [ ] T009 [P] Create `core/database.py` (async engine + sync engine + get_db)
- [ ] T010 [P] Create `core/redis.py` (3 clients + RedisKeys 16 patterns)
- [ ] T011 [P] Create `core/storage.py` (MinIO client + 5 buckets + magic byte validation)
- [ ] T012 Create `core/security.py` (JWT HS256 + bcrypt 12 + rate limit middleware + injection sanitizer)
- [ ] T013 [P] Create `core/logging.py` (structlog JSON + RequestIDMiddleware)
- [ ] T014 [P] Create `core/celery_config.py` (4 queues + 8 Beat tasks)
- [ ] T015 [P] Create `core/embeddings.py` (BGE-M3 stub — raises NotImplementedError until Phase 2a)
- [ ] T016 [P] Create `core/llm_router.py` (stub — raises NotImplementedError until Phase 2b)

---

## Phase 4: Users Module

- [ ] T017 Create `modules/users/models.py` (User, StudentProfile, LandlordProfile)
- [ ] T018 [P] Create `modules/users/schemas.py` (RegisterRequest, LoginResponse, OnboardingRequest, etc.)
- [ ] T019 Create `modules/users/repository.py` (get_by_email, create_user, save_profile)
- [ ] T020 Create `modules/users/service.py` (register, login, refresh, logout, onboarding)
- [ ] T021 Create `modules/users/router.py` (/auth/* + /users/onboarding)

---

## Phase 5: Housing Module

- [ ] T022 Create `modules/housing/models.py` (Listing, ListingPhoto, ListingVerification, SavedListing)
- [ ] T023 [P] Create `modules/housing/schemas.py`
- [ ] T024 Create `modules/housing/repository.py`
- [ ] T025 Create `modules/housing/service.py`
- [ ] T026 Create `modules/housing/router.py` (/listings/*)

---

## Phase 6: Stub Modules + App

- [ ] T027 [P] Create 8 stub modules (roommate, agent, fraud, contracts, area_intel, estimator, notifications, reputation) — `__init__.py` only
- [ ] T028 Create `app/main.py` (FastAPI factory + lifespan + routers)

**Checkpoint**: `curl http://localhost:8000/health` returns 200

---

## Phase 7: Tests

- [ ] T029 Create `tests/test_api_listings.py` (auth flow, CRUD, ownership, photo upload, filters)

**Checkpoint**: `docker compose exec api pytest tests/test_api_listings.py -v` — all pass

---

## Phase 8: Spec Validation

- [ ] T030 Create `specs/all_modules.yaml` (Phase 1 module contracts)

**Final gate**: `docker compose --profile spec run spec-validator`
