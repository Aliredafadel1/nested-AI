# Feature Specification: Phase 4 — Launch

**Feature Branch**: `004-launch`

**Created**: 2026-06-05

**Status**: Draft

**Scope**: Days 13–14. Demo mode, mobile polish, empty states, production readiness. No new features. Requires Phase 3 complete.

---

## User Scenarios & Testing

### User Story 1 — One-Click Demo Login as "Jawad" (Priority: P1)

A presenter clicks "Try Demo" on the login page. They are instantly logged in as a pre-seeded student persona named Jawad — with a complete profile, saved listings, a conversation history, and a landlord review already posted — without typing any credentials.

**Why this priority**: Demo reliability during a presentation is non-negotiable.

**Independent Test**: Click "Try Demo" → land on the feed as Jawad → all 8 user stories are demonstrable without additional setup.

**Acceptance Scenarios**:

1. **Given** the login page, **When** "Try Demo" is clicked, **Then** Jawad's JWT is issued and the feed loads with his pre-populated data within 2 seconds.
2. **Given** Jawad's session, **When** each of the 8 user stories is exercised, **Then** every feature responds with realistic data (no empty states, no loading errors).
3. **Given** a demo session ends, **When** Jawad logs out, **Then** his seed data is not modified (demo is read-heavy, not destructive).

---

### User Story 2 — Mobile Polish Passes Visual Review (Priority: P2)

Every screen in the app renders correctly at 375px (iPhone SE) with no horizontal overflow, no truncated labels, and touch targets ≥ 44px. The agent chat microphone button is prominent and easy to tap.

**Why this priority**: Primary audience is students on phones.

**Acceptance Scenarios**:

1. **Given** a 375px viewport, **When** each main page is viewed, **Then** no element overflows horizontally.
2. **Given** the agent chat on mobile, **When** the microphone button is visible, **Then** it has a minimum tap target of 44×44px.

---

### User Story 3 — Full Demo Rehearsed 5× Without Errors (Priority: P1)

The demo script is run end-to-end 5 times. All 5 runs complete without errors, timeouts, or unexpected empty states. The pitch narrative and 5 anticipated questions are prepared.

**Why this priority**: Presentation confidence requires repetition.

**Acceptance Scenarios**:

1. **Given** the demo script, **When** run 5 times consecutively, **Then** zero errors or loading failures occur.
2. **Given** the 5 anticipated questions, **When** answered, **Then** answers reference specific NestAI features and Lebanese context.

---

### Edge Cases

- What if the Jawad persona's seed data was accidentally modified by a previous session?
- What if an AI provider has an outage during the demo?
- What if the Docker host runs out of memory during the demo?

---

## Requirements

- **FR-001**: A "Try Demo" button MUST exist on the login page that issues Jawad's JWT without a password form.
- **FR-002**: Jawad's seed data MUST be resettable with a single command (for pre-demo reset).
- **FR-003**: All empty states MUST be implemented (feed, matches, notifications, saved listings).
- **FR-004**: Production Docker Compose MUST use `uvicorn` (not hot-reload) and all debug flags off.
- **FR-005**: Sentry error tracking MUST be configured and reporting in the production compose profile.

## Success Criteria

- **SC-001**: Demo runs 5× without a single error or timeout.
- **SC-002**: All 19 features from the brief are demonstrable via Jawad's persona.
- **SC-003**: `docker compose --profile spec run spec-validator` exits 0 on the production build.
- **SC-004**: Mobile Chrome at 375px — no horizontal overflow on any screen.

## Assumptions

- No new features are added in this phase — polish only.
- The demo machine has Docker, 16GB RAM, and internet access for LLM API calls.
- A pre-demo reset command exists to restore Jawad's seed data if needed.
