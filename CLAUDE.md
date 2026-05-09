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
python app.py          # starts on http://0.0.0.0:5000, auto-runs Alembic migrations
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

### Backend (`app.py` + `db/` + `auth.py`)

All Flask routes live in `app.py`. Auth is enforced by `@require_auth` from `auth.py`, which validates a Bearer token against `BUGTRACKER_TOKEN` (env var) or an agent key from the `agents` table.

The `db/` layer is a set of repository modules — one per domain object — that speak SQLAlchemy directly to SQLite. No ORM models; all queries use `text()` with explicit TypedDicts defined in `db/types.py`.

Key db modules:
- `db/bugs.py` — Bug CRUD; sanitizes HTML via `bleach` before write
- `db/lookup.py` — Generic `LookupRepo` shared by `products.py`, `areas.py`, `severities.py`, `platforms.py`
- `db/search.py` — `Fts5Backend` wrapping SQLite FTS5 queries
- `db/agents.py` — Agent key registration and per-agent rate limits
- `db/audit.py` — Append-only audit log written on every bug mutation

**Request flow:** route → `@require_auth` → repo function → SQLite + FTS5 → audit_log → JSON response

Rate limiting is applied globally (200/min) and per-endpoint (20/min for QR codes). Constants like `MAX_UPLOAD_MB` are named in `app.py`; don't hardcode magic numbers.

### Database & Migrations

Alembic migrations in `alembic/versions/` run automatically on `python app.py`. The FTS5 virtual table (`bugs_fts`) is kept in sync with `bugs` via INSERT/UPDATE/DELETE triggers defined in migration `0005`.

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

- **Auth everywhere:** every route uses `@require_auth`; agent keys live in the `agents` table with individual rate limits
- **Sanitization:** bleach on write (backend), DOMPurify on render (frontend) — both are required; don't remove either
- **FTS5 sync:** the triggers in migration `0005` keep `bugs_fts` consistent; any schema change to `bugs` must update the triggers
- **No ORM models:** queries use `sqlalchemy.text()` + TypedDicts from `db/types.py`
- **PostgreSQL path exists** in `db/connection.py` but is untested; SQLite is the only supported backend
