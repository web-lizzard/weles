---
change_id: backend-bootstrap
current_phase: 3
next_step: 3.1
next_command: /implement backend-bootstrap phase 3
updated: 2026-08-28
---

### Phase 1: Devcontainer — add uv and Postgres

#### Manual

- [ ] 1.1 Rebuild the devcontainer
- [ ] 1.2 `docker compose -f .devcontainer/docker-compose.yml ps` shows `postgres` healthy
- [ ] 1.3 `ordo status` succeeds inside the rebuilt container

### Phase 2: Backend project scaffolding

#### Automated

- [x] 2.1 `cd backend && uv sync` exits 0 — b4d3d82
- [x] 2.2 `cd backend && uv run python -c "import backend"` exits 0 — b4d3d82

### Phase 3: Bootstrap contract — stubs

#### Automated

- [ ] 3.1 `cd backend && uv run python -c "from backend.config.settings import Settings"` exits 0
- [ ] 3.2 `cd backend && uv run python -c "from backend.main import app"` exits 0

### Phase 4: Bootstrap contract — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 `cd backend && uv run pytest` passes (health endpoint 200 `{"status": "ok"}` + `Settings` `ValidationError` on missing `database_url`)

#### Manual

- [ ] 4.2 `uv run fastapi dev` then `curl localhost:8000/health` returns `200 {"status": "ok"}`
