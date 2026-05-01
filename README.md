# GujRERA Gateway

FastAPI webapp that supports both:

- live on-demand GujRERA aggregation
- local SQLite persistence with FTS-backed retrieval and grounded query responses

## Run

```bash
docker compose up --build
```

Open `http://localhost:8000`.

## What it exposes

- `GET /api/projects`
- `GET /api/projects/{project_reg_id}`
- `GET /api/projects/{project_reg_id}/inventory`
- `GET /api/projects/{project_reg_id}/quarters`
- `GET /api/storage/summary`
- `POST /api/storage/sync`
- `GET /api/storage/runs/{run_id}`
- `GET /api/rag/search?q=...`
- `POST /api/rag/answer`
- `GET /health`

## Local Database

- The app stores its local SQLite database at `data/gujrera_local.db`.
- Docker Compose mounts `./data` into the container so the database persists locally.
- Use the UI or `POST /api/storage/sync` to sync project data into the local database.
- The sync stores:
  - project summary rows
  - full aggregated project detail JSON
  - normalized blocks, quarters, and inventory units
  - FTS-indexed RAG chunks for querying

## Notes

- Listing responses are cached in-process for one hour.
- Detail requests fan out to GujRERA concurrently and tolerate partial failures.
- Local retrieval uses SQLite FTS5 first, with a SQL `LIKE` fallback for awkward query strings.
- The runtime uses a legacy TLS compatibility setting because the GujRERA server still requires legacy renegotiation support.
