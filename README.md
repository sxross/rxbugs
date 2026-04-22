# RxBugs

Lightweight local bug tracker — Flask + SQLite + TypeScript SPA.

## Quick start

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment

```bash
cp .env.example .env
```

Edit `.env` and set `BUGTRACKER_TOKEN` to a random secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Run the server

```bash
source .venv/bin/activate
python app.py
```

The server starts on `http://0.0.0.0:5000`.  
Open `http://localhost:5000` in your browser and paste the token from `.env`.

**Mobile authentication**: After logging in on desktop, click "Show QR Code" to generate a QR code. Scan it with your phone to log in instantly without typing the long token.

**Note**: On first run, you must initialize the database schema manually:

```bash
alembic upgrade head
```

The migrations are **not** run automatically by the server (controlled by `RUN_MIGRATIONS` env var, default: false). This prevents accidental migrations in production.

### 4. Build the UI (optional)

The `static/` directory contains a pre-built UI. To rebuild after editing `src/`:

```bash
npm install
npm run build
```

During development, run the Vite dev server alongside Flask for hot-reload:

```bash
npm run dev   # proxies API calls to Flask on :5000
```

---

## launchd (start on login)

Edit `com.rxbugs.bugtracker.plist` and replace `REPLACE_WITH_YOUR_TOKEN` with your token.

```bash
cp com.rxbugs.bugtracker.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rxbugs.bugtracker.plist
```

Logs: `~/Library/Logs/bugtracker.log`

Stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.rxbugs.bugtracker.plist
```

---

## API

All requests require `Authorization: Bearer <token>`.

### Create a bug

```http
POST /bugs
Content-Type: application/json

{
  "product": "RxTrack",
  "title": "Memo card crashes on save",
  "area": "ui",
  "priority": 1,
  "severity": "showstopper"
}
```

### Search bugs

```http
GET /bugs?q=crash&priority=1&status=open
```

### Close a bug

```http
POST /bugs/BUG-0001/close
Content-Type: application/json

{
  "resolution": "fixed",
  "annotation": "Fixed in commit abc123."
}
```

### Register an agent

```http
POST /agents
Content-Type: application/json

{"name": "rxtrack-test-runner", "description": "CI test suite"}
```

The response includes the `key` field — save it, it is shown once.

---

## Database Migrations

Migrations are managed via Alembic and must be run manually before starting the server:

```bash
alembic upgrade head
```

**Development**: To auto-run migrations on startup (e.g., for tests or local dev), set:

```bash
export RUN_MIGRATIONS=true
```

**Production**: Always run migrations as a separate deployment step. Never set `RUN_MIGRATIONS=true` in production.

## Rate Limiting

The app uses Flask-Limiter with in-memory storage by default (suitable for development only).

**Production**: Set `REDIS_URL` for shared rate limiting across processes/instances:

```bash
export REDIS_URL=redis://localhost:6379
```

Or use a Redis connection string with authentication:

```bash
export REDIS_URL=redis://:password@hostname:6379/0
```

You must install the Redis Python client:

```bash
pip install redis
```

Without Redis, rate limiting only works within a single process and resets on server restart.

---

## Migration path (SQLite → PostgreSQL)

1. Set `DATABASE_URL=postgresql+psycopg2://...` in `.env`
2. `pip install psycopg2-binary`
3. `alembic upgrade head` against the new database
4. Run `scripts/migrate_sqlite_to_pg.py` (one-time data migration)
5. Restart the server

No application code changes required.

---

## Project layout

```
app.py              Flask application + all API routes
db/
  connection.py     Engine factory + search backend selector
  types.py          Shared TypedDicts
  bugs.py           Bug CRUD
  annotations.py    Annotation log
  artifacts.py      File attachments
  relations.py      Bug-to-bug links
  products.py       Product management
  agents.py         Agent keys
  audit.py          Append-only audit log
  search.py         FTS5 search backend
alembic/            Database migrations
src/                TypeScript source (Vite build → static/)
static/             Compiled UI (committed, served by Flask)
uploads/            File attachments (gitignored)
```
