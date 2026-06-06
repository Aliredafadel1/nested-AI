# Feature Specification: Phase 3 — Frontend

**Feature Branch**: `003-frontend`

**Created**: 2026-06-05

**Status**: Draft

**Scope**: Days 8–12. React + Vite + Tailwind + shadcn/ui. UI for all Phase 1 and Phase 2 features. Requires Phase 2 complete.

---

## Clarifications

### Session 2026-06-06

- Q: What React state mechanism should manage JWT access tokens? → A: Option A — Zustand store. `useAuthStore` holds `{ accessToken, user, setToken, clear }`. No `localStorage` usage anywhere.
- Q: What library handles API data fetching? → A: Option A — TanStack Query (`useQuery`/`useMutation`) for all REST endpoints; raw `fetch` + `ReadableStream` for the agent SSE chat stream.
- Q: What do "inquiry counts" on the landlord dashboard represent? → A: Option A — count of students who saved the listing (`SELECT COUNT(*) FROM saved_listings WHERE listing_id = ?`). No new table or migration needed.
- Q: How do SSE notifications surface in the UI? → A: Option C — both: toast pop-up on real-time arrival (auto-dismiss 4s) AND a bell icon with count badge in the navbar plus a dropdown panel showing the last 20 notifications.
- Q: How does the frontend detect that a returning student has completed onboarding? → A: Option A — on login, call `GET /users/me` (or a profile endpoint); if `university_id` is non-null in the returned profile, route directly to the feed and skip onboarding.
- Q: Should an in-app floating AI chat widget be added? → A: Yes — a floating chat bubble (bottom-right corner, available across all pages) that opens the existing agent chat UI. Reuses the agent endpoint and streaming logic. External embeddable widget deferred to Phase 4.

---

## User Scenarios & Testing

### User Story 1 — Student Completes Onboarding and Lands on the Feed (Priority: P1)

A new student registers, sees an 8-question onboarding flow (university, budget, sleep schedule, study habits, cleanliness, guests, language, priorities), submits it, and lands on a listing feed pre-filtered by their preferences.

**Why this priority**: Onboarding feeds all AI features — without it, embeddings and agent context are incomplete.

**Independent Test**: Complete the 8-question form → profile is saved → listing feed renders.

**Acceptance Scenarios**:

1. **Given** a new student, **When** they complete all 8 onboarding questions, **Then** `student_profiles` is updated and they are redirected to the listing feed.
2. **Given** an incomplete onboarding, **When** the student skips a required question, **Then** a validation error appears inline (not a page reload).
3. **Given** a returning student, **When** they log in, **Then** onboarding is skipped and they go directly to the feed.

---

### User Story 2 — Student Views Listing Feed with Map and Badges (Priority: P1)

The listing feed shows cards with price, bedrooms, neighbourhood, fraud badge (red/yellow/green), and verification badge. A Leaflet map shows pins for all visible listings. Clicking a pin highlights the card.

**Why this priority**: Primary discovery surface.

**Independent Test**: Feed renders 50 seed listings with correct badges; map pins appear.

**Acceptance Scenarios**:

1. **Given** seed listings with fraud scores, **When** the feed loads, **Then** listings with `fraud_score ≥ 0.7` show a red "High Risk" badge.
2. **Given** a listing with `phone_verified: true`, **When** it appears in the feed, **Then** a green "Verified" badge is shown.
3. **Given** a Leaflet map, **When** a pin is clicked, **Then** the corresponding listing card scrolls into view and is highlighted.

---

### User Story 3 — Student Chats with the AI Agent (Priority: P1)

The agent chat UI streams responses token-by-token. A microphone button starts voice recording (Whisper STT). Area score bars and a "Compare 2 areas" button appear in the sidebar. Quick-action chips for common Lebanese survival queries ("generator hours?", "water delivery?") appear below the input.

**Why this priority**: Main AI interface — must work on mobile.

**Independent Test**: Send a text query → streaming response renders correctly → voice button records and fills the input field.

**Acceptance Scenarios**:

1. **Given** a student types a query, **When** the agent responds, **Then** tokens stream progressively (not a single payload dump).
2. **Given** the microphone button is pressed, **When** the student speaks and releases, **Then** Whisper transcription fills the chat input within 3 seconds.
3. **Given** the agent returns area scores, **When** they appear in the sidebar, **Then** each score renders as a labelled progress bar (electricity, internet, transport, safety, student vibe).

---

### User Story 4 — Student Reviews a Contract (Priority: P2)

The contract UI shows a PDF upload zone, a loading spinner during analysis, and color-coded risk cards (red/yellow/green) once done. Each card shows the clause text and a plain-language explanation.

**Why this priority**: Students must understand risk before signing — visual clarity is critical.

**Independent Test**: Upload a test PDF → spinner appears → risk cards render with correct colors.

**Acceptance Scenarios**:

1. **Given** a PDF upload, **When** analysis completes, **Then** risk cards appear grouped by severity (high first, then medium, then low).
2. **Given** a high-severity clause, **When** the card renders, **Then** it has a red left border, a warning icon, and the clause text is quoted.
3. **Given** OCR was used, **When** the result renders, **Then** a notice "Scanned document — OCR used" appears above the cards.

---

### User Story 5 — Landlord Manages Their Dashboard (Priority: P2)

The landlord dashboard shows their posted listings, inquiry counts, and a cost estimator. The estimator takes rent + neighbourhood and returns a breakdown: generator, water, internet, transport, total.

**Why this priority**: Supply side needs a management interface.

**Independent Test**: Landlord logs in → sees their listings → cost estimator returns a breakdown.

**Acceptance Scenarios**:

1. **Given** a landlord with 2 listings, **When** they open the dashboard, **Then** both listings appear with inquiry counts and edit/delete controls.
2. **Given** the cost estimator form, **When** rent and neighbourhood are submitted, **Then** a breakdown with 5 line items (generator, water, internet, transport, total) appears.

---

### Edge Cases

- What does the feed look like with 0 listings (empty state)?
- What if the agent stream connection drops mid-response?
- What if a user uploads a non-PDF to the contract analyzer?
- What if voice recording is denied by the browser?
- Mobile viewport: do all components render correctly at 375px width?

---

## Requirements

- **FR-001**: JWT access tokens MUST be stored in a Zustand store (`useAuthStore`). `localStorage` usage for tokens is forbidden.
- **FR-002**: Agent chat MUST use raw `fetch` + `ReadableStream` for SSE streaming. All other API calls use TanStack Query.
- **FR-003**: Voice input MUST use `MediaRecorder` API → `POST /agent/transcribe` → fill input field.
- **FR-004**: All pages MUST render correctly at 375px width (mobile-first).
- **FR-005**: Empty states MUST exist for: listing feed, saved listings, roommate matches, notifications.
- **FR-006**: The app MUST work without a page reload for token refresh (silent background refresh via TanStack Query mutation).
- **FR-007**: Landlord dashboard MUST show per-listing saved count from `saved_listings` table as "inquiry count".
- **FR-008**: SSE notifications MUST surface as: (a) toast pop-up on real-time arrival (auto-dismiss 4s) AND (b) bell icon with count badge + dropdown panel showing last 20 notifications.
- **FR-009**: On login, `GET /users/me` (or profile endpoint) MUST be called; if `university_id` is non-null, route directly to the feed, bypassing onboarding.
- **FR-010**: A floating chat bubble MUST appear in the bottom-right corner on all authenticated pages. Clicking it opens the agent chat panel as a slide-in drawer. The bubble shows an unread-message count badge when the agent has responded. Reuses the existing `POST /agent/chat` SSE endpoint — no new backend required.

## Success Criteria

- **SC-001**: All 5 user stories (onboarding, feed+map, agent chat, contract analyzer, landlord dashboard) are demonstrable via the UI.
- **SC-002**: Agent streaming chat works on mobile Chrome (375px).
- **SC-003**: No `localStorage` calls for auth tokens anywhere in the React codebase — verified by `grep localStorage src/`.
- **SC-004**: Leaflet map renders with all seed listing pins without errors.
- **SC-005**: Notification toast appears within 1 second of a server-sent event; bell badge count increments.

## Assumptions

- Phase 2 API is running and all endpoints are accessible at `localhost:8000`.
- shadcn/ui components are used for all form elements and cards.
- No separate mobile app — responsive web only.
- State management: Zustand (`zustand` package). Data fetching: TanStack Query (`@tanstack/react-query`).
- Routing: React Router v6 (`react-router-dom`).
- Map: Leaflet + `react-leaflet` wrapper.
