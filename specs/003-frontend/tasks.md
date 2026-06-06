# Tasks: Phase 3 — Frontend

**Input**: specs/003-frontend/plan.md + spec.md (clarified 2026-06-06)
**5 User Stories + 1 Floating Widget** | Stack: React 18 + Vite + Tailwind + shadcn/ui + Zustand + TanStack Query

---

## Phase 1: No DB Migration

No schema changes needed. All tables exist. Proceed directly to backend additions.

---

## Phase 2: Backend Additions (2 new endpoints)

**Purpose**: Add `GET /users/me` (onboarding bypass check) and `GET /listings/{id}/stats` (landlord inquiry count). No new modules, no migrations.

- [ ] T001 Add `UserMeOut` schema to `modules/users/schemas.py`:
  ```python
  class UserMeOut(BaseModel):
      id: int
      email: str
      role: str
      profile: StudentProfileOut | dict | None = None
      model_config = {"from_attributes": True}
  ```

- [ ] T002 Add `get_profile_for_user(user_id, role)` to `modules/users/repository.py`:
  - If role == "student": `SELECT * FROM student_profiles WHERE user_id = ?`
  - If role == "landlord": `SELECT * FROM landlord_profiles WHERE user_id = ?`
  - Returns dict or None

- [ ] T003 Add `get_me(user_id, role)` to `modules/users/service.py`:
  - Loads user from repo + profile from new repo method
  - Returns `UserMeOut`

- [ ] T004 Add `GET /users/me` to `modules/users/router.py`:
  ```python
  @router.get("/users/me", response_model=UserMeOut)
  async def get_me(current_user=Depends(get_current_user), db=Depends(get_db)):
      redis = get_async_redis()
      svc = UserService(db, redis)
      result = await svc.get_me(int(current_user["sub"]), current_user["role"])
      await redis.aclose()
      return result
  ```

- [ ] T005 [P] Add `get_saved_count(listing_id)` to `modules/housing/repository.py`:
  ```python
  async def get_saved_count(self, listing_id: int) -> int:
      result = await self._db.execute(
          text("SELECT COUNT(*) FROM saved_listings WHERE listing_id = :lid"),
          {"lid": listing_id}
      )
      return result.scalar_one() or 0
  ```

- [ ] T006 [P] Add `get_listing_stats(listing_id, landlord_id)` to `modules/housing/service.py`:
  - Verify ownership via `_get_own_listing`
  - Call `repo.get_saved_count(listing_id)`
  - Return `{"listing_id": listing_id, "saved_count": count}`

- [ ] T007 [P] Add `GET /listings/{id}/stats` to `modules/housing/router.py`:
  ```python
  @router.get("/{listing_id}/stats")
  async def listing_stats(listing_id: int, current_user=Depends(require_landlord), db=Depends(get_db)):
      return await HousingService(db).get_listing_stats(listing_id, int(current_user["sub"]))
  ```

**Checkpoint**: `curl -H "Authorization: Bearer <token>" http://localhost:8000/users/me` returns JSON with profile. `curl .../listings/1/stats` returns `{listing_id, saved_count}`.

---

## Phase 3: Frontend Scaffold

**Purpose**: Create the React project, configure tooling, and establish the app shell before building any features.

- [ ] T008 Scaffold frontend project in `frontend/`:
  ```bash
  cd frontend
  npm create vite@latest . -- --template react-ts
  npm install
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```
  Configure `tailwind.config.ts` to scan `./src/**/*.{ts,tsx}`.
  Add Tailwind directives to `src/index.css`.

- [ ] T009 [P] Install all dependencies:
  ```bash
  npm install \
    @tanstack/react-query \
    zustand \
    react-router-dom \
    react-hook-form @hookform/resolvers zod \
    leaflet react-leaflet @types/leaflet \
    react-hot-toast \
    react-dropzone \
    lucide-react \
    clsx tailwind-merge
  ```
  Install shadcn/ui: `npx shadcn-ui@latest init` (choose Tailwind, React, TypeScript).
  Install shadcn components: `npx shadcn-ui@latest add button card input label select radio-group progress badge toast dialog`.

- [ ] T010 Create `src/stores/authStore.ts`:
  ```typescript
  import { create } from 'zustand'
  interface AuthState {
    accessToken: string | null
    user: { id: number; email: string; role: string } | null
    setAuth: (token: string, user: AuthState['user']) => void
    setToken: (token: string) => void
    clear: () => void
  }
  export const useAuthStore = create<AuthState>(set => ({
    accessToken: null,
    user: null,
    setAuth: (accessToken, user) => set({ accessToken, user }),
    setToken: (accessToken) => set({ accessToken }),
    clear: () => set({ accessToken: null, user: null }),
  }))
  ```

- [ ] T011 [P] Create `src/stores/chatStore.ts`:
  ```typescript
  // isOpen, messages[], sessionId, toggle(), addMessage(), setSessionId()
  ```

- [ ] T012 [P] Create `src/stores/notifStore.ts`:
  ```typescript
  // unreadCount, notifications[], increment(), decrement(), setAll(), markRead(id)
  ```

- [ ] T013 Create `src/api/client.ts` — base fetch wrapper:
  - Reads `useAuthStore.getState().accessToken`
  - Adds `Authorization: Bearer <token>` header
  - On 401: calls `POST /api/auth/refresh` silently → `useAuthStore.setToken(new_token)` → retries once
  - On second 401: `useAuthStore.clear()` → redirect to `/login`
  - Base URL: `import.meta.env.VITE_API_URL || 'http://localhost:8000'`

- [ ] T014 Create `src/App.tsx` with React Router v6 routes and TanStack Query provider:
  ```tsx
  <QueryClientProvider client={queryClient}>
    <Toaster position="top-right" />
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<AuthLayout />}>
          <Route path="/onboarding" element={<OnboardingPage />} />
        </Route>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/listings" />} />
          <Route path="/listings" element={<FeedPage />} />
          <Route path="/listings/:id" element={<ListingDetailPage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/contracts" element={<ContractsPage />} />
          <Route path="/roommate" element={<RoommatePage />} />
          <Route path="/dashboard" element={<LandlordDashboard />} />
          <Route path="/notifications" element={<NotificationsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
  ```

- [ ] T015 Create layout components:
  - `src/components/layout/AuthLayout.tsx` — centered card, no navbar
  - `src/components/layout/AppLayout.tsx` — Navbar + `<Outlet />` + `FloatingChatWidget` + SSE notification connection
  - `src/components/layout/Navbar.tsx` — logo, nav links (role-aware), `NotificationBell`, user menu with logout
  - `src/components/shared/ProtectedRoute.tsx` — redirects to `/login` if no `accessToken`

**Checkpoint**: `npm run dev` starts without errors. `/login` renders a blank page with correct title.

---

## Phase 4: Auth Pages + API Hooks

- [ ] T016 Create `src/api/users.ts`:
  - `register(data)` → `POST /auth/register`
  - `login(data)` → `POST /auth/login`
  - `logout()` → `POST /auth/logout`
  - `refresh()` → `POST /auth/refresh`
  - `getMe()` → `GET /users/me`
  - `onboard(data)` → `POST /users/onboarding`

- [ ] T017 Create `src/pages/LoginPage.tsx`:
  - shadcn/ui Card + Form (react-hook-form + zod)
  - On submit: `login()` → `setAuth()` → `getMe()` → route based on `university_id` and `role`
  - Link to `/register`

- [ ] T018 [P] Create `src/pages/RegisterPage.tsx`:
  - Role select (student / landlord)
  - On success: same routing logic as login

- [ ] T019 Create `src/pages/OnboardingPage.tsx`:
  - 8-step wizard with `Progress` bar
  - Steps: university (select from seeded unis), budget range, sleep_schedule, study_habits, cleanliness, guests, language, priorities (multi-select)
  - On submit: `onboard()` → redirect to `/listings`
  - Guard: if `getMe()` returns non-null `university_id`, redirect to `/listings` immediately

**Checkpoint**: Register → login → onboarding flow completes. Returning student skips onboarding.

---

## Phase 5: Listing Feed + Map

- [ ] T020 Create `src/api/listings.ts`:
  - `useListings(filters)` — TanStack `useQuery` → `GET /listings?...`
  - `useListing(id)` — `GET /listings/{id}`
  - `saveListing(id)` / `unsaveListing(id)` — `useMutation`
  - `useSavedListings()` — `GET /listings/saved`
  - `useListingStats(id)` — `GET /listings/{id}/stats` (landlord)

- [ ] T021 Create `src/api/fraud.ts`:
  - `useFraudReport(listingId)` — TanStack `useQuery` → `GET /fraud/{id}`

- [ ] T022 Create shared components:
  - `src/components/shared/EmptyState.tsx` — icon + message + optional CTA button
  - `src/components/shared/LoadingSpinner.tsx` — centered spinner

- [ ] T023 Create `src/components/listings/ListingBadge.tsx`:
  - Accepts `fraud_score` and `phone_verified`
  - Returns: red "High Risk" (≥0.7), yellow "Moderate" (0.4–0.7), green "Verified" (phone_verified)

- [ ] T024 Create `src/components/listings/ListingCard.tsx`:
  - Props: listing object
  - Shows: photo (first photo URL or placeholder), title, price (USD), bedrooms, neighbourhood, badges
  - Save/unsave heart button (student only)
  - Click → navigate to `/listings/:id`
  - Highlight state via `data-highlighted` + ring border (used by map)

- [ ] T025 Create `src/components/listings/ListingFilters.tsx`:
  - Neighbourhood select (hardcoded 8 options)
  - Price range: min/max number inputs
  - Bedrooms select (1/2/3/Any)
  - onChange → parent updates query params

- [ ] T026 Create `src/components/listings/ListingMap.tsx`:
  - `react-leaflet` MapContainer centred on Beirut (33.89, 35.50), zoom 13
  - Markers for each listing with lat/lng
  - On marker click: emit `onPinClick(listing_id)` → parent scrolls card into view
  - Leaflet CSS imported in component

- [ ] T027 Create `src/pages/FeedPage.tsx`:
  - Split layout: filters + cards (left) | map (right, hidden on mobile, tab toggle on mobile)
  - `useListings(filters)` for data
  - Map pin click → `scrollIntoView` + set highlighted card id
  - Empty state when no results
  - Error state with retry button

- [ ] T028 Create `src/pages/ListingDetailPage.tsx`:
  - Full listing details from `useListing(id)`
  - Photo carousel (shadcn/ui Carousel or simple prev/next)
  - Save/unsave button
  - Fraud report accordion (collapsed, expandable via `useFraudReport`)
  - "Ask AI about this listing" → `useChatStore.toggle()` + pre-fill query

**Checkpoint**: Feed shows 50 seed listings. Map renders pins. Clicking a pin highlights the card. Fraud badges visible.

---

## Phase 6: Agent Chat + Floating Widget

- [ ] T029 Create `src/api/agent.ts`:
  - `streamChat(query, sessionId)` → `fetch POST /agent/chat` → returns `ReadableStream`
  - `transcribeAudio(blob)` → `POST /agent/transcribe` with `FormData`
  - `useAreaScores(name)` → TanStack `useQuery` → `GET /areas/{name}`
  - `compareAreas(a, b)` → TanStack `useMutation` → `POST /areas/compare`

- [ ] T030 Create `src/components/agent/VoiceButton.tsx`:
  - `MediaRecorder` on mousedown/touchstart, stop on mouseup/touchend
  - Sends blob to `transcribeAudio()` → fills input via `onTranscript(text)` callback
  - Shows recording indicator (red pulsing dot) while recording
  - On browser permission denial: shows tooltip "Microphone access denied"

- [ ] T031 Create `src/components/agent/QuickChips.tsx`:
  - Row of pill buttons: "Generator hours?", "Water delivery?", "Safe area?", "Contract help?"
  - `onClick` → calls parent's `onSubmit(chip_text)`

- [ ] T032 Create `src/components/agent/ChatMessage.tsx`:
  - Displays a single message (user or agent)
  - Agent message: left-aligned, shows streaming cursor while `isStreaming`
  - User message: right-aligned, bubble style

- [ ] T033 Create `src/components/agent/AreaScoreSidebar.tsx`:
  - Labelled progress bars for: electricity (hours/day ÷ 24), internet, transport, safety, student_vibe (all /5)
  - "Compare 2 Areas" button → opens a dialog with two area selects → calls `compareAreas`
  - Hidden on mobile (shown only on desktop via `hidden lg:block`)

- [ ] T034 Create `src/components/agent/ChatPanel.tsx` — core shared component:
  - Message list (scrollable, auto-scrolls to bottom on new message)
  - `QuickChips` below input
  - Input row: text field + `VoiceButton` + Send button
  - On send: call `streamChat(query, sessionId)`:
    - Add user message to `useChatStore`
    - Add empty agent message with `isStreaming: true`
    - Read `ReadableStream` line-by-line, parse `data:` events, append tokens
    - On `[DONE]`: set `isStreaming: false`
    - On stream error: show "Connection lost — retrying…", retry once after 2s
  - Min height: 400px on desktop, full-height on mobile

- [ ] T035 Create `src/pages/AgentPage.tsx`:
  - Two-column layout (desktop): `AreaScoreSidebar` (left 280px) + `ChatPanel` (flex-1)
  - Mobile: `ChatPanel` full width, sidebar hidden
  - Student-only route guard

- [ ] T036 Create `src/components/layout/FloatingChatWidget.tsx`:
  - Reads `useChatStore.isOpen`
  - Bubble: `fixed bottom-6 right-6 z-50` — 56px circle, brand primary colour
  - Unread badge: red circle with count, shown when agent replied since last open
  - Panel: `fixed bottom-24 right-6 w-96 h-[600px] z-50` — shadcn/ui Card with shadow + `ChatPanel`
  - Close button (×) in panel header
  - Renders in `AppLayout` — available on every authenticated page
  - Uses same `useChatStore` as `AgentPage` — session shared across pages

**Checkpoint**: Open `/agent` → type a query → tokens stream in. Open widget on `/listings` → chat works. Voice button fills input.

---

## Phase 7: Contracts, Roommate, Notifications

- [ ] T037 Create `src/api/contracts.ts`:
  - `uploadContract(file)` → `useMutation` → `POST /contracts/analyze`
  - `useContract(id)` → `useQuery` → `GET /contracts/{id}`, refetch every 3s while `status !== 'complete'`

- [ ] T038 Create `src/components/contracts/RiskCard.tsx`:
  - Props: `{ level, clause_text, explanation }`
  - High: `border-l-4 border-red-500` + ⚠️ icon
  - Medium: `border-l-4 border-yellow-500`
  - Low: `border-l-4 border-green-500`

- [ ] T039 Create `src/components/contracts/ContractUpload.tsx`:
  - `react-dropzone` zone — accepts PDF only
  - Shows file name after drop
  - Submit button → calls `uploadContract(file)` → returns `contract_id`

- [ ] T040 Create `src/pages/ContractsPage.tsx`:
  - `ContractUpload` component
  - On upload success: polls `useContract(id)` every 3s
  - Shows `LoadingSpinner` while `status !== 'complete'`
  - Shows `RiskCard[]` sorted high→medium→low when complete
  - OCR banner when `ocr_used: true`
  - Error message if `status: 'failed'`

- [ ] T041 Create `src/api/roommate.ts`:
  - `useRoommateMatches()` → `useQuery` → `GET /roommate/matches`
  - `sendRequest(to_user_id)` → `useMutation` → `POST /roommate/requests`

- [ ] T042 Create `src/components/roommate/DimensionScores.tsx`:
  - 5 labelled progress bars: sleep, study, cleanliness, guests, budget
  - Each bar: label + percentage fill

- [ ] T043 Create `src/components/roommate/MatchCard.tsx`:
  - Shows: user_id, overall score (0–1 as %), `DimensionScores`
  - "Send Request" button → `sendRequest(user_id)` → shows ✓ on success

- [ ] T044 Create `src/pages/RoommatePage.tsx`:
  - `useRoommateMatches()` for data
  - 422 response → show "Complete onboarding to see matches"
  - Empty state: "No matches yet — check back after more students join"
  - Grid of `MatchCard`

- [ ] T045 Create `src/api/notifications.ts`:
  - `useNotifications()` → `useQuery` → `GET /notifications`
  - `markRead(id)` → `useMutation` → `POST /notifications/{id}/read`
  - `connectSSE(onMessage)` — opens `GET /notifications/stream`, parses events, calls `onMessage`

- [ ] T046 Create `src/components/layout/NotificationBell.tsx`:
  - Bell icon (lucide-react) with badge showing `useNotifStore.unreadCount`
  - Click → toggle `NotificationPanel`

- [ ] T047 Create `src/components/layout/NotificationPanel.tsx`:
  - Dropdown (shadcn/ui Popover) with last 20 notifications from `useNotifications()`
  - Click notification → `markRead(id)` → `notifStore.decrement()`
  - Empty state: "No notifications yet"

- [ ] T048 Create `src/pages/NotificationsPage.tsx`:
  - Full list of all notifications
  - Same mark-read interaction

- [ ] T049 Wire SSE in `AppLayout.tsx`:
  - `useEffect(() => connectSSE(msg => { notifStore.increment(); toast(msg.payload) }), [])`
  - Disconnect on unmount

**Checkpoint**: Upload a PDF → spinner → risk cards appear. `/roommate` shows matches. Bell badge increments when notification arrives.

---

## Phase 8: Landlord Dashboard + Estimator

- [ ] T050 Create `src/api/areas.ts`:
  - `useAreaScores(name)` → `GET /areas/{name}`
  - `compareAreas(a, b)` → `POST /areas/compare`

- [ ] T051 Create `src/api/estimator.ts`:
  - `calculateCost(rent, neighbourhood_id)` → `useMutation` → `POST /estimator/calculate`

- [ ] T052 Create `src/pages/LandlordDashboard.tsx`:
  - Listings table: `useListings()` + per-listing `useListingStats(id)` for saved_count
  - Edit listing → `PUT /listings/{id}` via mutation → shadcn/ui Dialog form
  - Delete listing → `DELETE /listings/{id}` → confirmation Dialog
  - "New Listing" button → Dialog form → `POST /listings`
  - Cost Estimator section:
    - Form: rent (number) + neighbourhood (select)
    - Submit → `calculateCost()` mutation
    - Results table: rent, generator, water, internet, transport, **total_monthly**
    - If `commute_minutes` is null: show "—"

**Checkpoint**: Landlord logs in → sees their listings with saved counts. Cost estimator returns breakdown.

---

## Phase 9: Mobile Polish + Empty States

- [ ] T053 [P] Audit all pages at 375px viewport (Chrome DevTools mobile):
  - FeedPage: map shown as tab (not side-by-side), full-width cards
  - AgentPage: full-width chat, no sidebar
  - ContractsPage: full-width upload zone
  - Navbar: hamburger menu or icon-only nav
  - FloatingChatWidget: panel width `w-full` on mobile (not fixed 384px)
  - Fix any horizontal overflow with `overflow-x-hidden` or layout adjustments

- [ ] T054 [P] Add remaining empty states:
  - `FeedPage`: "No listings match your filters — try broadening your search"
  - `SavedListings` (within FeedPage): "You haven't saved any listings yet"
  - `RoommatePage`: handled in T044
  - `NotificationsPage`: "No notifications yet"

- [ ] T055 [P] Add error boundaries:
  - Wrap each page in a simple `ErrorBoundary` component
  - Show "Something went wrong — refresh the page" on uncaught errors

**Checkpoint**: All pages render correctly at 375px. No horizontal overflow on any screen.

---

## Phase 10: Regression Test (Backend)

- [ ] T056 Run Phase 1+2a+2b regression to ensure backend additions didn't break anything:
  ```bash
  docker compose exec api pytest tests/ -v
  ```
  All 49 tests must pass.

- [ ] T057 [P] Run spec validator:
  ```bash
  docker compose --profile spec run spec-validator
  ```

---

## Dependency Graph

```
T001→T002→T003→T004 (users/me)
T005→T006→T007 (listing stats)
                    ↓
T008→T009→T010→T011→T012→T013→T014→T015 (scaffold + app shell)
                    ↓
            T016→T017→T018→T019 (auth pages)
                    ↓
            T020→T021→T022→T023→T024→T025→T026→T027→T028 (feed + map)
                    ↓
            T029→T030→T031→T032→T033→T034→T035→T036 (agent + widget)
                    ↓
            T037→T038→T039→T040 (contracts) [parallel with T041→T044 roommate]
            T045→T046→T047→T048→T049 (notifications)
                    ↓
            T050→T051→T052 (landlord dashboard)
                    ↓
            T053, T054, T055 [parallel — mobile polish]
                    ↓
            T056, T057 [parallel — regression + validation]
```

---

**Final gate**: `docker compose --profile spec run spec-validator && docker compose exec api pytest tests/ -v`
