# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RxBugs is a lightweight self-hosted bug tracker with a Flask REST API backend and a TypeScript single-page application frontend. Data is stored in SQLite with FTS5 full-text search.

## Commands

### Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then set BUGTRACKER_TOKEN
RUN_MIGRATIONS=true python app.py   # starts on http://0.0.0.0:5000 (set RUN_MIGRATIONS for first run)
```

### Frontend
```bash
npm install
npm run build          # Vite → static/ (pre-built copy already committed)
npm run dev            # hot-reload dev server, proxies /api to Flask on :5000
```

### Tests
```bash
pytest                            # all tests
pytest tests/test_api_bugs.py     # single file
pytest -k test_create             # match by name
```

### TypeScript
```bash
npx tsc --noEmit                  # type-check only
```

## Architecture

### Backend (`app.py` + `routes/` + `db/` + `auth.py`)

`app.py` is a thin ~145-line entry point: it initializes the engine, service layer, rate limiter, and registers four Flask blueprints. All route logic lives in `routes/`:

- `routes/auth.py` — QR code / session token login flow (unauthenticated endpoints)
- `routes/bugs.py` — Bug CRUD, annotations, relations; uses `BugService` for close
- `routes/artifacts.py` — File upload/download with `ALLOWED_EXTENSIONS` allowlist and `secure_filename`
- `routes/admin.py` — Products, areas, severities, platforms, agent management

Auth is enforced by `@require_auth` from `auth.py`, which validates a Bearer token against `BUGTRACKER_TOKEN` or an agent key from the `agents` table. `auth.py` exposes `require_auth`, `bad`, and `init_auth(token, engine)` — import from there, never redefine inline.

**Request flow:** route → `@require_auth` → service or repo → SQLite + FTS5 → audit_log → JSON response

The `services/` layer handles multi-step operations that need a single transaction. `BugService.close_bug_with_annotation()` is the canonical example: it computes warnings, closes the bug, and optionally appends an annotation atomically. Add new cross-repo logic here rather than in routes.

`schemas/bugs.py` defines Pydantic models (`BugCreate`, `BugUpdate`, `CloseRequest`) used by `routes/bugs.py` for request validation and type coercion.

The `db/` layer is a set of repository modules that speak SQLAlchemy directly to SQLite. No ORM models; all queries use `text()` with explicit TypedDicts defined in `db/types.py`.

Key db modules:
- `db/bugs.py` — Bug CRUD; sanitizes HTML via `bleach` before write
- `db/lookup.py` — Generic `LookupRepo` shared by `products.py`, `areas.py`, `severities.py`, `platforms.py`
- `db/search.py` — `Fts5Backend`; `query()` returns `{bugs, total, page, per_page}` with LIMIT/OFFSET pagination
- `db/agents.py` — Agent key registration and per-agent rate limits
- `db/audit.py` — Append-only audit log written on every bug mutation

Rate limiting: 200/min globally, 20/min for QR endpoints. Set `REDIS_URL` for production (default is in-memory, which resets on restart). Named constants (`MAX_UPLOAD_MB`, `DEFAULT_RATE_LIMIT`, etc.) live in `app.py` — don't hardcode magic numbers.

### Database & Migrations

Alembic migrations live in `alembic/versions/`. They do **not** run automatically — set `RUN_MIGRATIONS=true` to run them on startup (for dev/CI only; run `alembic upgrade head` manually in production). The FTS5 virtual table (`bugs_fts`) is kept in sync with `bugs` via INSERT/UPDATE/DELETE triggers defined in migration `0005`.

### Frontend (`src/`)

`src/main.ts` bootstraps the SPA: reads the URL hash, picks a view class, and mounts it. Views are in `src/views/`:

- `ListView.ts` — Bug list with filter/search UI
- `DetailView.ts` — Single bug + annotations, artifacts, relations
- `BugForm.ts` — Create/edit form
- `AdminView.ts` — Generic lookup-table manager (products, areas, severities, platforms) using `renderLookupTable()`
- `CloseDialog.ts` — Confirm-close modal

`src/api.ts` is the sole HTTP layer — a thin fetch wrapper that adds the Bearer token header. All user-generated HTML rendered in views must go through DOMPurify; Markdown is rendered with Marked then sanitized.

### Tests (`tests/`)

`conftest.py` provides:
- `engine` — fresh in-memory SQLite DB for repo-layer tests
- `client` — Flask test client with a fixed token
- `auth_headers` — `{"Authorization": "Bearer <token>"}`

API tests wipe mutable tables between tests; repo tests get isolated DBs. Test files are split by feature (`test_api_bugs.py`, `test_api_annotations.py`, etc.).

## Key Constraints

- **Auth everywhere:** every route uses `@require_auth` from `auth.py`; agent keys live in the `agents` table with individual rate limits
- **Sanitization:** bleach on write (backend), DOMPurify on render (frontend) — both are required; don't remove either
- **FTS5 sync:** the triggers in migration `0005` keep `bugs_fts` consistent; any schema change to `bugs` must update the triggers
- **No ORM models:** queries use `sqlalchemy.text()` + TypedDicts from `db/types.py`
- **File uploads:** always validate with `_allowed_file()` and sanitize with `secure_filename()`; set `X-Content-Type-Options: nosniff` on downloads
- **Migrations are manual in production:** `RUN_MIGRATIONS` defaults to `false`; never set it `true` in prod
- **PostgreSQL path exists** in `db/connection.py` but is untested; SQLite is the only supported backend
