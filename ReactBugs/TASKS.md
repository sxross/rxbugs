# ReactBugs — Rebuild Task List

React 18 + TypeScript + TanStack Query + React Router v6 + Tailwind CSS.
Backend: existing Flask API unchanged.
Flow: code feature → test → fix until green → commit → next task.

---

## Phase 0 — Foundation

- [ ] **Task 1: TASKS.md** — this file
- [ ] **Task 2: Scaffold** — Vite + React 18 + TypeScript in `ReactBugs/`, add React Router v6 + TanStack Query v5 + Tailwind CSS, Vite proxy `/api → :5000`; done when `npm run dev` loads a blank page
- [ ] **Task 3: Types + API layer** — port `types.ts` verbatim, port `api.ts` fetch wrapper with Bearer header; done when `tsc --noEmit` passes
- [ ] **Task 4: Auth context** — `useAuth` hook, token read/write from `localStorage`; done when token survives a page refresh
- [ ] **Task 5: Login page** — `/login` route, fetch QR code, poll for session token, redirect to `/bugs` on success
- [ ] **Task 6: ProtectedRoute** — wrapper that redirects unauthenticated users to `/login`; done when `/bugs` without a token bounces to login

## Phase 1 — Bug List

- [ ] **Task 7: Bug list page** — `/bugs`, fetch `GET /api/bugs`, render rows (title, status, product, priority, created_at); no filters yet
- [ ] **Task 8: Status filter** — open/closed/all toggle, synced to URL search params
- [ ] **Task 9: Multi-select filters** — product, area, platform dropdowns, URL-synced
- [ ] **Task 10: Priority + severity filters** — URL-synced; done when all filter combos produce the right API call
- [ ] **Task 11: FTS search input** — debounced, URL-synced
- [ ] **Task 12: Pagination** — page/per_page controls, URL-synced; done when back/forward browser nav restores the right page

## Phase 2 — Bug Detail

- [ ] **Task 13: Bug detail page** — `/bugs/:id`, fetch `GET /api/bugs/:id`, render all header fields
- [ ] **Task 14: Annotations** — list annotations, add annotation form with optimistic update
- [ ] **Task 15: Artifacts list + download** — list files, download link with auth header
- [ ] **Task 16: File upload** — attach file to bug, invalidates artifact list on success
- [ ] **Task 17: Related bugs** — list relations, add/remove with search-by-id input
- [ ] **Task 18: Close dialog** — confirm modal, optional annotation field, PATCH close, invalidates detail query
- [ ] **Task 19: Reopen** — single button, PATCH reopen, invalidates detail query

## Phase 3 — Bug Form

- [ ] **Task 20: Create bug** — `/bugs/new`, all fields, populated selects from admin lookup endpoints, POST on submit
- [ ] **Task 21: Edit bug** — `/bugs/:id/edit`, pre-populated, PATCH on submit, shares form component with Task 20

## Phase 4 — Admin

- [ ] **Task 22: Admin shell** — `/admin` layout with tab nav (Products / Areas / Severities / Platforms / Agents)
- [ ] **Task 23: Lookup tables** — Products, Areas, Severities, Platforms: list + create + archive/unarchive; one generic component reused four times
- [ ] **Task 24: Agents** — list, create, activate/deactivate

## Phase 5 — Polish

- [ ] **Task 25: App header + nav** — links to Bugs / Admin, logout button, active-route highlight
- [ ] **Task 26: Error + loading states** — error boundary, loading skeletons on list and detail; done when killing the Flask server shows a graceful error, not a blank screen
- [ ] **Task 27: `tsc --noEmit` clean** — zero type errors
- [ ] **Task 28: `npm run build` clean** — Vite production build succeeds with no warnings
