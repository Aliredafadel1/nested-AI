# Implementation Plan: Phase 3 — Frontend

**Status**: Ready to implement
**Based on**: specs/003-frontend/spec.md (clarified 2026-06-06)
**Depends on**: Phase 2b complete — all 10 API modules running

---

## Constitution Check

| Principle | Status |
|-----------|--------|
| JWT in React memory only (Zustand store, never localStorage) | ✓ FR-001 / FR-010 |
| No WebSocket — SSE only for agent stream + notifications | ✓ FR-002 / FR-008 |
| Security-first: token refresh silent, no credentials in URL | ✓ FR-006 |
| Lebanon-aware by default: USD prices, Arabic/French/English text support | ✓ |
| Graceful degradation: empty states, loading states, stream drop handling | ✓ FR-005 |
| Mobile-first: 375px renders for all pages | ✓ FR-004 |

---

## 1. Architecture Decisions

### Stack
| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | React 18 + Vite | spec requirement |
| Styling | Tailwind CSS + shadcn/ui | spec requirement |
| State | Zustand (`useAuthStore`, `useChatStore`, `useNotificationStore`) | clarified |
| Data fetching | TanStack Query v5 | clarified |
| Agent SSE | raw `fetch` + `ReadableStream` | clarified |
| Routing | React Router v6 | standard for Vite SPA |
| Map | Leaflet + react-leaflet | spec requirement |
| Notifications | react-hot-toast (toasts) + custom bell panel | clarified |
| Icons | lucide-react | ships with shadcn/ui |

### Zustand Stores
```
useAuthStore   → { accessToken, user: {id, email, role}, setAuth, clear }
useChatStore   → { isOpen, messages, sessionId, toggle, addMessage }
useNotifStore  → { unreadCount, notifications, increment, markRead }
```

### Route Map
```
/                     redirect → /listings (student) | /dashboard (landlord) | /login
/login                LoginPage         (public)
/register             RegisterPage      (public)
/onboarding           OnboardingPage    (student, skipped if profile complete)
/listings             FeedPage          (public — map + cards)
/listings/:id         ListingDetailPage (public)
/agent                AgentPage         (student)
/contracts            ContractsPage     (student)
/roommate             RoommatePage      (student)
/dashboard            LandlordDashboard (landlord)
/notifications        NotificationsPage (authenticated)
```

### Floating Chat Widget (FR-010)
- Fixed `bottom-6 right-6 z-50` on every authenticated page
- Collapsed state: circular button (56px) with chat icon + unread-response badge
- Expanded state: slide-in drawer (`w-96`, from right) containing the full `<ChatPanel />`
- Shares `useChatStore` with `AgentPage` — same session, same messages
- Drawer can be dismissed without losing the conversation

### Component Tree (key components only)
```
App
├── AuthLayout (public: login, register)
└── AppLayout (authenticated)
    ├── Navbar
    │   ├── NotificationBell → NotificationPanel
    │   └── UserMenu
    ├── <Outlet /> (routed page)
    └── FloatingChatWidget
        └── ChatPanel (shared with AgentPage)
```

---

## 2. Minimal Backend Additions (Phase 3 needs)

Two new endpoints added to the existing backend — no new modules, no migrations.

### `GET /users/me`
Added to `modules/users/router.py`:
```
GET /users/me
  auth: bearer
  response: {
    id: int, email: str, role: str,
    profile: {
      university_id: int | null,   ← key for onboarding-bypass check
      budget_min: int | null,
      budget_max: int | null,
      sleep_schedule: str | null,
      ... (full StudentProfileOut or LandlordProfileOut)
    } | null
  }
```

### `GET /listings/{id}/stats`
Added to `modules/housing/router.py` (landlord-only):
```
GET /listings/{id}/stats
  auth: bearer(landlord, own)
  response: { listing_id: int, saved_count: int }
```

Update `specs/all_modules.yaml` with both endpoints.

---

## 3. Page & Component Specs

### LoginPage / RegisterPage
- shadcn/ui `Card` + `Form` (react-hook-form + zod validation)
- On success: store token in `useAuthStore` → call `GET /users/me` → route
- "Try Demo" button (Phase 4) — placeholder rendered but disabled in Phase 3

### OnboardingPage
- 8-step progress indicator (shadcn/ui `Progress`)
- Each step: single question with shadcn/ui `RadioGroup` or `Select`
- Submit calls `POST /users/onboarding` → redirect to `/listings`
- Skipped if `GET /users/me` returns non-null `university_id`

### FeedPage (Listing Feed + Map)
Split layout (desktop: side-by-side, mobile: stacked):
- Left: `ListingFilters` + `ListingCard` grid
- Right: `ListingMap` (Leaflet, pins from current visible listings)
- Map pin click → scroll card into view + highlight border
- `ListingCard` badges:
  - Red "High Risk" if `fraud_score ≥ 0.7`
  - Yellow "Moderate Risk" if `0.4 ≤ fraud_score < 0.7`
  - Green "Verified" if `phone_verified: true`
- Filters: neighbourhood dropdown, price range slider, bedrooms select
- Empty state: `<EmptyState>` component with "No listings found" message
- TanStack Query: `useListings(filters)` → `GET /listings?...`

### ListingDetailPage
- Full listing details + photo carousel
- "Save" / "Unsaved" toggle → `POST/DELETE /listings/{id}/save`
- Fraud report section (collapsed, expandable) → `GET /fraud/{listing_id}`
- "Ask AI about this listing" button → opens `FloatingChatWidget` with pre-filled query

### AgentPage (full-page chat)
- Left sidebar (desktop only, hidden on mobile):
  - Area score bars (electricity, internet, transport, safety, student_vibe)
  - "Compare 2 Areas" button → `POST /areas/compare`
- Main: `ChatPanel` (shared component with `FloatingChatWidget`)
- `ChatPanel` internals:
  - Message history (scrollable)
  - Quick-action chips: "Generator hours?", "Water delivery?", "Cheapest area?", "Contract tips?"
  - Input row: text field + VoiceButton + Send
  - `VoiceButton`: `MediaRecorder` API → blob → `POST /agent/transcribe` → fill input
  - Streaming: `fetch POST /agent/chat` → `ReadableStream` → append tokens to last message
  - On stream drop: show "Connection lost — reconnecting…" inline message, auto-retry once

### ContractsPage
- `ContractUpload`: drag-and-drop zone (react-dropzone) + file picker, PDF only
- On upload: `POST /contracts/analyze` → show spinner
- Poll `GET /contracts/{id}` every 3s until `status: complete | failed`
- Results: `RiskCard[]` sorted high → medium → low
  - High: red left border + ⚠️ icon + clause quote + explanation
  - Medium: yellow left border
  - Low: green left border
  - If `ocr_used: true`: banner "Scanned document — OCR used"

### RoommatePage
- `MatchCard` grid — shows name, overall score, 5 dimension bars
- "Send Request" button → `POST /roommate/requests`
- Empty state if no embeddings yet: "Complete onboarding to see matches"
- 422 from API → show "Your profile is being processed. Check back shortly."

### LandlordDashboard
- Listing table: title, price, neighbourhood, saved_count (from `GET /listings/{id}/stats`), status, Edit/Delete actions
- "New Listing" button → modal form
- Cost Estimator section: form (rent + neighbourhood) → `POST /estimator/calculate` → breakdown table
- Edit: PATCH listing → `PUT /listings/{id}`
- Delete: soft-delete → `DELETE /listings/{id}` (confirmation dialog)

### NotificationsPage
- Full list view of all notifications (`GET /notifications`)
- Click to mark read (`POST /notifications/{id}/read`)

### FloatingChatWidget (FR-010)
- Visible on all authenticated pages (rendered in `AppLayout`)
- State from `useChatStore`
- Bubble: `fixed bottom-6 right-6` — 56px circle, brand colour
- Unread badge: shown when agent has replied since last open
- Panel: `fixed bottom-24 right-6 w-96 h-[600px]` — shadcn/ui `Card` with shadow
- Close button in panel header
- Same `<ChatPanel />` used in AgentPage — no duplicated logic

### Notification System
- On app mount (authenticated): connect SSE `GET /notifications/stream`
- On `data:` event → `useNotifStore.increment()` + `toast(notification.payload.message)`
- Bell icon in Navbar: red badge with `unreadCount`
- Click bell: toggle `NotificationPanel` dropdown (last 20 from `GET /notifications`)
- Click notification in panel: `POST /notifications/{id}/read` → decrement badge

---

## 4. Auth Flow Detail

```
1. POST /auth/login → { access_token } body + Set-Cookie: refresh_token (HttpOnly)
2. useAuthStore.setAuth(access_token, decoded_user)
3. GET /users/me → check profile.university_id
4. Route to /onboarding (null) or /listings (non-null)

Silent refresh (401 interceptor in api/client.ts):
5. On 401 response → POST /auth/refresh (sends HttpOnly cookie automatically)
6. New access_token → useAuthStore.setToken(new_token)
7. Retry original request

Logout:
8. POST /auth/logout → useAuthStore.clear() → navigate('/login')
```

---

## 5. API Client (`src/api/client.ts`)

Single `apiFetch(path, options)` wrapper:
- Reads `accessToken` from `useAuthStore.getState()` (Zustand outside React)
- Sets `Authorization: Bearer <token>` header
- On 401: attempts one silent refresh, retries, then redirects to `/login`
- TanStack Query `queryFn` and `mutationFn` all use this wrapper

---

## 6. Test Plan (manual — no browser automation in Phase 3)

Start dev server `npm run dev` in `frontend/`, verify these golden paths:

| Scenario | Steps | Expected |
|----------|-------|----------|
| New student onboarding | Register → 8-step form → submit | Redirected to feed, profile saved |
| Feed loads | Open /listings | 50 seed cards + map pins rendered |
| Fraud badge | Check Dekwaneh listing | Red badge on high-fraud-score card |
| Map pin click | Click map pin | Card scrolls into view + highlighted |
| Agent chat (text) | Type query → send | SSE tokens stream token-by-token |
| Agent chat (voice) | Click mic → speak → release | Input filled within 3s |
| Floating widget | Navigate to /listings → click bubble | Chat panel slides in, session preserved |
| Contract upload | Upload PDF → wait | Risk cards appear grouped by severity |
| Notifications | Trigger a notification | Toast appears + bell count increments |
| Landlord dashboard | Login as landlord → /dashboard | Listings + saved counts visible |
| Mobile 375px | DevTools mobile viewport → all pages | No horizontal overflow |
| Token refresh | Wait 15min → make request | Silent refresh, no logout |

---

## 7. Files to Create

```
frontend/
  package.json
  vite.config.ts
  tailwind.config.ts
  tsconfig.json
  index.html
  src/
    main.tsx
    App.tsx
    stores/
      authStore.ts
      chatStore.ts
      notifStore.ts
    api/
      client.ts
      users.ts
      listings.ts
      agent.ts
      roommate.ts
      fraud.ts
      areas.ts
      estimator.ts
      contracts.ts
      notifications.ts
    pages/
      LoginPage.tsx
      RegisterPage.tsx
      OnboardingPage.tsx
      FeedPage.tsx
      ListingDetailPage.tsx
      AgentPage.tsx
      ContractsPage.tsx
      RoommatePage.tsx
      LandlordDashboard.tsx
      NotificationsPage.tsx
    components/
      layout/
        AppLayout.tsx
        AuthLayout.tsx
        Navbar.tsx
        FloatingChatWidget.tsx
        NotificationBell.tsx
        NotificationPanel.tsx
      listings/
        ListingCard.tsx
        ListingBadge.tsx
        ListingMap.tsx
        ListingFilters.tsx
      agent/
        ChatPanel.tsx
        ChatMessage.tsx
        VoiceButton.tsx
        QuickChips.tsx
        AreaScoreSidebar.tsx
      contracts/
        ContractUpload.tsx
        RiskCard.tsx
      roommate/
        MatchCard.tsx
        DimensionScores.tsx
      shared/
        EmptyState.tsx
        LoadingSpinner.tsx
        ProtectedRoute.tsx
```

### Modified backend files
```
modules/users/router.py     — add GET /users/me
modules/users/service.py    — add get_me() method
modules/users/repository.py — add get_profile_by_user_id() method
modules/users/schemas.py    — add UserMeOut schema
modules/housing/router.py   — add GET /listings/{id}/stats
modules/housing/service.py  — add get_listing_stats() method
modules/housing/repository.py — add get_saved_count() method
specs/all_modules.yaml      — add both new endpoints
```

---

Run `/nest-tasks` to generate the ordered task breakdown.
