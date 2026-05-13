# ReactBugs

React 18 / TypeScript frontend for RxBugs — a lightweight self-hosted bug tracker.
Replaces the original vanilla-TS SPA with React + TanStack Query (client-side reactive
caching). The Flask REST API backend is unchanged; this app proxies all API calls to it
during development.

## Tech stack

| Layer | Library |
|---|---|
| UI | React 18, TypeScript |
| Routing | React Router v6 |
| Data fetching | TanStack Query v5 |
| Styling | Tailwind CSS v4 |
| Build | Vite 6 |
| Tests | Vitest + Testing Library |
| Lint | ESLint 9 (flat config) |

## Prerequisites

- Node 20+
- The RxBugs Flask API running on `http://localhost:5000` (see root `README.md`)

## Setup

```bash
cd ReactBugs
npm install
```

Copy the example env file if you want to override the API base URL (optional — the
Vite proxy handles it automatically during development):

```bash
# No .env needed for local dev; the proxy is configured in vite.config.ts
```

## Common commands

```bash
# Start the hot-reload dev server (proxies /bugs /auth /agents /api → :5000)
npm run dev

# Type-check without emitting
npm run typecheck

# Lint all source files
npm run lint

# Run tests (watch mode)
npm test

# Run tests once with coverage report
npm run coverage

# Production build (runs tsc + vite build)
npm run build

# Preview the production build locally
npm run preview
```

## Project structure

```
ReactBugs/
├── src/
│   ├── api.ts               # Typed fetch wrapper; reads token from localStorage
│   ├── types.ts             # Shared TypeScript interfaces (mirrors Flask schema)
│   ├── main.tsx             # App entry — providers: QueryClient, Router, Auth
│   ├── App.tsx              # Route table
│   ├── context/
│   │   └── AuthContext.tsx  # useAuth hook + AuthProvider
│   ├── components/
│   │   ├── AppLayout.tsx    # Persistent header + nav
│   │   ├── ErrorBoundary.tsx
│   │   └── ProtectedRoute.tsx
│   ├── views/
│   │   ├── LoginPage.tsx    # Paste-token + QR-code login
│   │   ├── BugListPage.tsx  # List + filters + pagination (all URL-synced)
│   │   ├── BugDetailPage.tsx# Detail, annotations, attachments, relations, close
│   │   ├── BugFormPage.tsx  # Create + edit (shared component)
│   │   └── AdminPage.tsx    # Products / Areas / Severities / Platforms / Agents
│   └── test/
│       ├── setup.ts         # jest-dom + localStorage stub
│       └── utils.tsx        # renderWithProviders helper
├── vite.config.ts
├── vitest.config.ts
├── eslint.config.js
└── tsconfig.app.json
```

## Authentication

Sign in by pasting the `BUGTRACKER_TOKEN` from the Flask `.env` file into the login
form. On desktop you can also click **Show QR Code** to generate a scannable login
link for a mobile device.

Once signed in the token is stored in `localStorage` under `bugtracker_token`. Sign
out via the header button to clear it.

## Development notes

- All server state lives in TanStack Query. Mutations call `queryClient.invalidateQueries`
  to keep the cache fresh; the annotation form uses an optimistic update.
- Artifact downloads use a manual `fetch` with the `Authorization` header because
  `<a download>` can't attach headers.
- The Vite proxy rewrites `/bugs`, `/auth`, `/agents`, and `/api` to Flask on `:5000`.
  Do **not** start the React dev server on port 5000.
