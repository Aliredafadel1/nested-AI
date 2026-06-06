# Feature Specification: NestAI Platform — Full Build

**Feature Branch**: `001-nestai-platform`

**Created**: 2026-06-05

**Status**: Draft

**Input**: NestAI_Complete_Brief.pdf — 14-day sprint, 19 features, 10 modules, 13 Docker services

---

## User Scenarios & Testing

### User Story 1 — Student Finds a Safe Apartment via AI Agent (Priority: P1)

A Lebanese university student opens NestAI, completes onboarding (budget, university, sleep schedule, cleanliness preferences), then asks the AI agent in Arabic: "I need a 1-bedroom near AUB under $600 with a generator, quiet at night." The agent searches listings, filters by fraud score, calculates commute times, and returns 3 ranked results with trade-off explanations and real monthly cost (including generator subscription).

**Why this priority**: Core value proposition — replaces hours of manual search with one AI conversation.

**Independent Test**: Student can complete a full search conversation and receive ranked, fraud-checked results without any other feature working.

**Acceptance Scenarios**:

1. **Given** an onboarded student, **When** they send a natural-language query to `/agent/chat`, **Then** the agent returns ≥1 listing with commute time, area score, fraud status, and estimated monthly cost within one response.
2. **Given** the agent returns a listing, **When** the response is validated by `validate_coherence`, **Then** every cited listing ID exists in the database.
3. **Given** a GPT-4o mini timeout, **When** the agent's cheap-tier call fails, **Then** the fallback chain resolves and the student receives a response (not a 500 error).

---

### User Story 2 — Student Detects a Scam Before Wiring Money (Priority: P1)

A student views a listing that appears suspiciously cheap. NestAI's fraud system has flagged it: the price is 2.4 standard deviations below the neighbourhood median, the phone number is linked to 3 other listings, and two photos have duplicate perceptual hashes from known scam listings. The student sees a red "High Fraud Risk" badge with specific evidence items.

**Why this priority**: Protects students from the most common and costly failure mode of apartment hunting in Lebanon.

**Independent Test**: Can be fully tested by submitting a listing that meets fraud thresholds and verifying the badge and evidence list appear in the listing feed.

**Acceptance Scenarios**:

1. **Given** a listing with price z-score > 2.0, **When** the fraud module runs its check, **Then** `fraud_reports.score` ≥ 0.7 and `price_zscore` is stored.
2. **Given** a listing photo that matches a known scam photo's phash (hamming distance ≤ 10), **When** the Celery dedup task runs, **Then** `listing_photos.phash` triggers a fraud flag.
3. **Given** a landlord phone number already linked to 2+ listings, **When** a new listing is submitted, **Then** the phone dedup check fires and adds a `phone_flags` entry to `fraud_reports.evidence`.

---

### User Story 3 — Student Understands Their Lease Before Signing (Priority: P1)

A student uploads a scanned PDF of a handwritten Arabic/French lease. The contract analyzer extracts text (or falls back to GPT-4o Vision OCR if PyMuPDF returns empty), passes it to Claude Sonnet, and returns a color-coded risk report: red clauses (automatic eviction without notice), yellow clauses (hidden fees, ambiguous renewal terms), and green clauses (standard, acceptable terms).

**Why this priority**: Contracts in Lebanon are often designed to confuse — analysis before signing is protective.

**Independent Test**: Upload a PDF with a known red-flag clause and verify the analysis JSON contains at least one `"risk": "high"` item.

**Acceptance Scenarios**:

1. **Given** a text-extractable PDF, **When** `/contracts/analyze` is called, **Then** the response contains `risk_items` with `level` (high/medium/low), `clause_text`, and `explanation` for each flagged clause.
2. **Given** a scanned/image PDF where PyMuPDF returns empty text, **When** the OCR fallback runs, **Then** GPT-4o Vision processes the images and the same `risk_items` schema is returned.
3. **Given** a contract analysis request, **When** Claude Sonnet is used, **Then** the analysis is stored in `contracts.analysis` as JSONB and `contracts.ocr_used` records whether OCR was needed.

---

### User Story 4 — Student Finds a Compatible Roommate (Priority: P2)

A student completes the 8-question onboarding (sleep schedule: night owl, study: quiet, cleanliness: high, guests: rarely, budget: $400-600). NestAI computes a 1024-dim BGE-M3 embedding of their profile. When they view potential roommates, 5 dimension-specific compatibility scores appear as progress bars — not just a total — so they can make informed trade-offs.

**Why this priority**: Roommate compatibility reduces the most common post-move conflict.

**Independent Test**: Two profiles with contrasting sleep schedules should score < 0.5 on the sleep dimension and this should be testable independently.

**Acceptance Scenarios**:

1. **Given** two student profiles with embeddings, **When** `/roommate/matches` is called, **Then** the response includes `score` (0-1) and `dimensions` with keys: `sleep`, `study`, `cleanliness`, `guests`, `budget`.
2. **Given** a student sends a roommate request, **When** the recipient accepts, **Then** both students receive an SSE notification and `roommate_requests.status` is `accepted`.
3. **Given** a profile embedding update (new preference), **When** the `update_preference_vector` Celery task runs, **Then** match scores are recalculated.

---

### User Story 5 — Landlord Lists a Verified Property (Priority: P2)

A landlord registers, verifies their phone number, posts a listing with photos and price, and receives a "Phone Verified" badge. The listing is embedded by BGE-M3 in the background via Celery. If the price is within the neighbourhood range, a "Price Verified" badge also appears.

**Why this priority**: Supply side of the marketplace — no listings means no student value.

**Independent Test**: A landlord can post a listing and see it appear in the public feed with the correct verification badges, testable without any AI feature.

**Acceptance Scenarios**:

1. **Given** a verified landlord, **When** `POST /listings` is called with valid data and photos, **Then** the listing appears in `GET /listings` with `status: active` and `phone_verified: true`.
2. **Given** a new listing, **When** the Celery `embed_listing` task runs, **Then** `listings.embedding` is populated with a 1024-dim vector.
3. **Given** a listing price within 1.5 standard deviations of the neighbourhood median, **When** the price check runs, **Then** `listing_verifications.price_in_range` is `true`.

---

### User Story 6 — Student Uses Voice to Search (Priority: P3)

A student taps the microphone button on mobile, speaks in Lebanese Arabic: "بدي شقة قريبة من LAU بـ 500 دولار". The audio is sent to `/agent/transcribe`, Whisper-1 transcribes it, and the text is inserted into the agent chat input field. The agent processes it identically to typed input.

**Why this priority**: Mobile-first market; typing Arabic is slow on phone keyboards.

**Independent Test**: Upload a webm audio file to `/agent/transcribe` and verify the JSON response contains transcribed text.

**Acceptance Scenarios**:

1. **Given** a webm audio file ≤25MB, **When** `POST /agent/transcribe` is called, **Then** the response contains `{ "text": "<transcribed string>" }` within 5 seconds.
2. **Given** an audio file >25MB, **When** the endpoint receives it, **Then** a 400 error is returned before the file reaches MinIO.

---

### User Story 7 — Student Gets Real Monthly Cost Breakdown (Priority: P3)

A student clicks "Estimate Full Cost" on a listing. The estimator module returns a detailed breakdown: rent ($550), generator subscription ($40/month based on neighbourhood), water delivery ($15), internet ($30), transport to LAU ($20) — total: $655/month. The hidden costs students never see on listing sites.

**Why this priority**: Lebanon's true cost of living is systematically underrepresented in listings.

**Independent Test**: Call `/estimator/calculate` with a listing ID and university ID; verify the response contains all 5 cost line items.

**Acceptance Scenarios**:

1. **Given** a listing ID and university ID, **When** `POST /estimator/calculate` is called, **Then** the response contains `rent`, `generator`, `water`, `internet`, `transport`, and `total_monthly` in USD.
2. **Given** a neighbourhood with known generator cost data, **When** the estimate is generated, **Then** `generator` matches the neighbourhood's `generator_cost` attribute.

---

### User Story 8 — Student Reads Neighbourhood Intelligence (Priority: P3)

A student clicks on a neighbourhood on the Leaflet map and sees an area intelligence card: electricity hours per day (18h), generator cost ($35/month), internet quality (4/5), transport score (3/5), safety score (4/5), student vibe score (5/5). They can compare two neighbourhoods side-by-side.

**Why this priority**: Neighbourhood-level data is unavailable anywhere else for Lebanese students.

**Independent Test**: Call `GET /areas/hamra` and verify all 6 score dimensions are returned.

**Acceptance Scenarios**:

1. **Given** a seeded neighbourhood, **When** `GET /areas/{name}` is called, **Then** the response includes `electricity_hours`, `generator_cost`, `internet`, `transport`, `safety`, `student_vibe`.
2. **Given** two neighbourhood names, **When** `POST /areas/compare` is called, **Then** the response includes side-by-side scores for both.

---

### Edge Cases

- What happens when all LLM providers are unavailable simultaneously?
- How does the agent handle a query with no matching listings (after 2x area/budget widening retries)?
- What if a landlord submits a listing photo with a corrupt magic byte header?
- What if a contract PDF is password-protected?
- What happens when a student's session expires mid-conversation?
- How does the system handle Arabic-only input in the roommate matching embedding?

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST support two user roles: `student` and `landlord`, plus an internal `admin` role for SFTP uploads.
- **FR-002**: System MUST implement a 6-node LangGraph agent with 9 MCP tools and 3-layer memory (Redis short-term, PostgreSQL long-term, pgvector semantic).
- **FR-003**: System MUST detect fraudulent listings via price z-score, phone dedup, and perceptual photo hashing.
- **FR-004**: System MUST analyze PDF and scanned lease contracts and return structured risk items with severity levels.
- **FR-005**: System MUST compute roommate compatibility across 5 dimensions using 1024-dim BGE-M3 embeddings.
- **FR-006**: System MUST calculate real monthly cost including generator, water, internet, and transport for any listing + university pair.
- **FR-007**: System MUST support real-time notifications via SSE + Redis pub/sub (no WebSockets).
- **FR-008**: System MUST validate all file uploads via magic byte inspection before writing to MinIO.
- **FR-009**: System MUST transcribe voice input (Arabic/French/English) via OpenAI Whisper-1.
- **FR-010**: System MUST run spec validation (`spec-validator`) before every deploy and fail the deploy if it doesn't exit 0.
- **FR-011**: System MUST support bulk admin data ingestion via SFTP (CSV listings, JSON area scores, PDF documents) with Celery-watched processing.
- **FR-012**: All 10 modules MUST communicate only through service interfaces — no cross-module repository imports.

### Key Entities

- **Listing**: price (USD), bedrooms, amenities, neighbourhood, landlord, embedding (1024-dim), fraud_score, verification status
- **Student Profile**: university, budget, sleep/study/cleanliness/guests preferences, embedding (1024-dim), preference_vector
- **Agent Session**: state JSONB, history JSONB, LLM-generated summary, linked student_memory
- **Contract**: MinIO key, OCR flag, analysis JSONB (risk_items with level/clause/explanation), status
- **Neighbourhood**: electricity_hours, generator_cost, internet/transport/safety/student_vibe scores (all 1-5)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Agent returns ranked, fraud-checked results in ≤8 seconds for a typical search query (p95).
- **SC-002**: Contract analysis completes in ≤30 seconds for a 10-page PDF (p95).
- **SC-003**: All 13 Docker services start and pass health checks with a single `docker compose up` command.
- **SC-004**: Spec validator exits 0 against all 10 module YAML contracts at project completion.
- **SC-005**: Full test suite (3 test files) passes against real PostgreSQL and Redis containers.
- **SC-006**: LLM cost achieves ≥85% reduction vs. routing everything through GPT-4o, measured by TASK_TIERS distribution.
- **SC-007**: Demo mode (one-click Lara persona login) loads and demonstrates all 8 user stories end-to-end.

## Assumptions

- The platform targets Lebanese students; USD pricing is correct for this market.
- Seed data covers 8 Beirut neighbourhoods and 50 listings sufficient for demo purposes.
- BGE-M3 is loaded locally — no embedding API cost or rate limits.
- OSRM routing server is seeded with Lebanon's OpenStreetMap data.
- A single developer builds this in a 14-day sprint following the phase plan in CLAUDE.md.
- Production deployment is Docker Compose on a single VPS — not Kubernetes.
- The "Lara" demo persona is a pre-seeded student account with complete onboarding for presentation use.
