# GujRERA Gateway

Stateless FastAPI webapp that pulls the public GujRERA APIs on demand, aggregates project detail data, and serves a browser UI from the same container.

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
- `GET /health`

## Notes

- No database, scheduler, or persistent state.
- Listing responses are cached in-process for one hour.
- Detail requests fan out to GujRERA concurrently and tolerate partial failures.
- The runtime uses a legacy TLS compatibility setting because the GujRERA server still requires legacy renegotiation support.
