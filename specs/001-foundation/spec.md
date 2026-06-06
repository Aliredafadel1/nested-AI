# Feature Specification: Phase 1 — Foundation

**Feature Branch**: `001-foundation`

**Created**: 2026-06-05

**Status**: Draft

**Scope**: Days 1–3. Database, Docker Compose, JWT auth, Listings CRUD, file uploads. No AI features.

---

## User Scenarios & Testing

### User Story 1 — Landlord Posts a Listing (Priority: P1)

A landlord registers, verifies their phone number, and posts a listing with title, price (USD), bedrooms, amenities, neighbourhood, and up to 20 photos. The listing appears in the public feed with a "Phone Verified" badge.

**Why this priority**: No listings = no platform. This is the supply side.

**Independent Test**: A landlord can register, post a listing with photos, and see it in `GET /listings` — testable with no other feature.

**Acceptance Scenarios**:

1. **Given** a registered landlord, **When** `POST /listings` is called with valid data, **Then** the listing appears in `GET /listings` with `status: active`.
2. **Given** a listing photo upload, **When** the file's magic bytes are invalid, **Then** the upload returns 400 before writing to MinIO.
3. **Given** a non-landlord JWT, **When** `POST /listings` is called, **Then** the response is 403.

---

### User Story 2 — Student Browses and Saves Listings (Priority: P1)

A student registers (or browses anonymously), views the listings feed, filters by neighbourhood and price, and saves a listing to their profile.

**Why this priority**: Demand side. Students need to see listings before any AI feature matters.

**Independent Test**: Anonymous `GET /listings` returns seeded listings. Student `POST /listings/{id}/save` works.

**Acceptance Scenarios**:

1. **Given** 50 seed listings, **When** `GET /listings` is called anonymously, **Then** all active listings are returned.
2. **Given** a `?neighbourhood=hamra&max_price=600` filter, **When** `GET /listings` is called, **Then** only matching listings are returned.
3. **Given** an authenticated student, **When** `POST /listings/{id}/save` is called, **Then** the listing appears in `GET /listings/saved`.

---

### User Story 3 — JWT Auth Works for Both Roles (Priority: P1)

A student and a landlord can register, log in, receive a 15-minute access token in the response body and a 7-day refresh token as an HttpOnly cookie, and refresh silently.

**Why this priority**: Auth gates every other feature.

**Independent Test**: Register → login → call a protected endpoint → refresh token → call again. All succeed.

**Acceptance Scenarios**:

1. **Given** valid credentials, **When** `POST /auth/login` is called, **Then** the response body contains `access_token` and a `Set-Cookie: refresh_token` HttpOnly header is set.
2. **Given** an expired access token and a valid refresh cookie, **When** `POST /auth/refresh` is called, **Then** a new access token and rotated refresh cookie are returned and the old refresh key is deleted from Redis.
3. **Given** a logout, **When** `POST /auth/logout` is called, **Then** the Redis refresh key is deleted immediately.

---

### Edge Cases

- What if a landlord tries to edit another landlord's listing?
- What if the MinIO bucket doesn't exist at startup?
- What if two listings are posted with the same photo (dedup is Phase 2, but the upload should not fail)?
- What if the seed SQL runs twice (idempotency)?

---

## Clarifications

### Session 2026-06-05

- Q: When a landlord deletes a listing, should it be a hard delete or soft delete? → A: Soft delete — `status: inactive`, row stays in DB, hidden from feed. Protects Phase 2 FK integrity (fraud_reports, listing_verifications reference listing_id).
- Q: Does Phase 1 build the onboarding API endpoint or Phase 2a? → A: Phase 1 — `POST /users/onboarding` stores preferences in `student_profiles`. Keeps Phase 2a focused purely on embedding logic.
- Q: Phone verification — real SMS (Twilio) or mock flag? → A: Mock flag — landlord submits phone number, seed/admin sets `phone_verified: true` in DB. No Twilio dependency.
- Q: Neighbourhood on listing — plain string or FK to neighborhoods table? → A: FK — `listings.neighbourhood_id` references `neighborhoods.id`. Required for Phase 2b price z-score grouping.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST create all 16 tables and HNSW indexes via `migrations/init.sql` (idempotent).
- **FR-002**: All 13 Docker services MUST start and pass health checks with `docker compose up -d`.
- **FR-003**: MinIO MUST initialize 5 typed buckets on first run (`--profile init`).
- **FR-004**: JWT access tokens MUST have 15-minute lifetime; refresh tokens MUST have 7-day lifetime and be HttpOnly cookie only.
- **FR-005**: Listing photos MUST be validated via magic bytes before MinIO write. Max 5MB per file, 20 per listing.
- **FR-006**: `PUT /listings/{id}` MUST enforce ownership — landlord can only edit their own listings.
- **FR-008**: `DELETE /listings/{id}` MUST soft-delete only — sets `status: inactive`. Hard deletes are forbidden. Row must remain for Phase 2 FK references (fraud_reports, listing_verifications).
- **FR-010**: Phone verification MUST be a mock flag. `phone_verified` is set via seed data or admin. No SMS/Twilio integration.
- **FR-007**: Seed data MUST load 50 realistic Lebanese listings across 8 neighbourhoods and 10 universities.
- **FR-009**: `POST /users/onboarding` MUST be built in Phase 1 — stores student preferences (university, budget, sleep_schedule, study_habits, cleanliness, guests, language, priorities) in `student_profiles`. Required by Phase 2a for embedding.

### Key Entities

- **User**: id, email, password_hash (bcrypt 12), role (student/landlord/admin)
- **Listing**: price (USD), bedrooms, amenities JSONB, neighbourhood_id (FK → neighborhoods.id), landlord_id, status (active/inactive)
- **Listing Photo**: minio_key, listing_id (phash populated in Phase 2)

## Success Criteria

- **SC-001**: `docker compose up -d` starts all 13 services; `curl localhost:8000/health` returns 200.
- **SC-002**: `pytest tests/test_api_listings.py -v` — all tests pass against real PostgreSQL.
- **SC-003**: A landlord can register, post a listing with 2 photos, and retrieve it via `GET /listings` in under 1 second.
- **SC-004**: JWT refresh rotation works — old token invalidated, new token issued.

## Assumptions

- Docker and Docker Compose are installed on the dev machine.
- `.env.dev` is copied to `.env` before starting.
- MinIO, PostgreSQL, and Redis run in Docker — no external services needed.
- Seed listings use hardcoded realistic Beirut data (prices in USD, real neighbourhood names).
