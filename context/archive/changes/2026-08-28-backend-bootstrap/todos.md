---
change_id: backend-bootstrap
current_phase: 4
next_step:
next_command: /archive backend-bootstrap
updated: 2026-08-28
---

### Phase 1: Devcontainer — add uv and Postgres

#### Manual

- [x] 1.1 Rebuild the devcontainer — c0b829f
- [x] 1.2 `docker compose -f .devcontainer/docker-compose.yml ps` shows `postgres` healthy — c0b829f
- [x] 1.3 `ordo status` succeeds inside the rebuilt container — c0b829f

### Phase 2: Backend project scaffolding

#### Automated

- [x] 2.1 `cd backend && uv sync` exits 0 — b4d3d82
- [x] 2.2 `cd backend && uv run python -c "import main"` exits 0 — b4d3d82

### Phase 3: Bootstrap contract — stubs

#### Automated

- [x] 3.1 `cd backend && uv run python -c "from config.settings import Settings"` exits 0 — a1b63b2
- [x] 3.2 `cd backend && uv run python -c "from main import app"` exits 0 — a1b63b2

### Phase 4: Bootstrap contract — behavior

#### Tests

- [x] tests generated — 7a8d207

#### Automated

- [x] 4.1 `cd backend && uv run pytest` passes (health endpoint 200 `{"status": "ok"}` + `Settings` `ValidationError` on missing `database_url`) — 6803067

#### Manual

- [x] 4.2 `cd backend && uv run fastapi dev src/main.py` then `curl localhost:8000/health` returns `200 {"status": "ok"}`
