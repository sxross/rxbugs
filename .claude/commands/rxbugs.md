# RxBugs — interact with the local bug tracker

You are acting as a bug-tracker assistant for the RxBugs app running at
`http://localhost:5000`.

## Authentication

Read the bearer token from the project's `.env` file:

```bash
grep BUGTRACKER_TOKEN .env | cut -d= -f2
```

Use it as `Authorization: Bearer <token>` on every authenticated request.

## Discover the full API

```bash
curl -s http://localhost:5000/api | python3 -m json.tool
```

This returns the OpenAPI 3.0 spec with every endpoint, required fields, and
response schemas. No auth required.

## Common operations

### List open bugs

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  'http://localhost:5000/bugs?status=open&per_page=25' | python3 -m json.tool
```

Filter further with `&product=`, `&area=`, `&severity=`, `&priority=`,
`&q=<search term>`.

### Log a bug

```bash
curl -s -X POST http://localhost:5000/bugs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product": "<product>",
    "title": "<one-line summary>",
    "description": "<optional detail>",
    "area": "<optional>",
    "platform": "<optional>",
    "priority": 2,
    "severity": "<optional>"
  }' | python3 -m json.tool
```

Only `product` and `title` are required.

### Get bug detail (with annotations, artifacts, relations)

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/bugs/<bug_id> | python3 -m json.tool
```

### Update a bug

```bash
curl -s -X PATCH http://localhost:5000/bugs/<bug_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"priority": 1, "area": "backend"}' | python3 -m json.tool
```

### Close a bug

```bash
curl -s -X POST http://localhost:5000/bugs/<bug_id>/close \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"resolution": "fixed", "annotation": "Fixed in commit abc123."}' \
  | python3 -m json.tool
```

`resolution` must be one of: `fixed`, `duplicate`, `no_repro`, `wont_fix`.

### Reopen a bug

```bash
curl -s -X POST http://localhost:5000/bugs/<bug_id>/reopen \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Add an annotation

```bash
curl -s -X POST http://localhost:5000/bugs/<bug_id>/annotations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "Reproduced on macOS 14.4 with steps X, Y, Z."}' \
  | python3 -m json.tool
```

### List products / areas / severities / platforms

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/products | python3 -m json.tool
```

Replace `products` with `areas`, `severities`, or `platforms`.

## Triage workflow

A typical triage session:

1. Fetch open bugs: `GET /bugs?status=open`
2. For each bug, read its detail: `GET /bugs/<id>`
3. Update priority/area/severity as needed: `PATCH /bugs/<id>`
4. Close bugs that are resolved: `POST /bugs/<id>/close`
5. Add notes for anything deferred: `POST /bugs/<id>/annotations`

## Guidance

- Always read `.env` for the token; never ask the user to paste it.
- If the server is not running, tell the user to start it:
  `source .venv/bin/activate && python app.py`
- Prefer paginating large result sets with `&page=` / `&per_page=`.
- Bug IDs look like `BUG-0001`; use the exact ID returned by the API.
- When logging bugs reported by the user, ask for product and title at minimum.
  Infer reasonable defaults for optional fields from context.
