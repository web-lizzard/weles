# Backend Bootstrap — Plan Brief

> Full plan: `plan.md`

## What & Why

Install and bootstrap the Python backend service decided in `context/adrs/backend-stack` and `context/adrs/repo-shape`: a `uv`-managed FastAPI daemon, laid out hexagonally, with its full dependency set installed and a runnable health-check skeleton — so the next capability (notes adapter, outbox, auth) has a working foundation to build into.

## Starting Point

No application code exists yet — only `context/` planning artifacts and a single-Dockerfile devcontainer (Node 22, no Python, no Postgres).

## Desired End State

Rebuild the devcontainer → Postgres runs healthy alongside the app container → `uv sync` inside `backend/` installs everything → `uv run fastapi dev` serves a daemon whose `/health` route returns `200 {"status": "ok"}`.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Dependency/env manager | `uv` | Fast, single lockfile, current Astral-documented FastAPI pattern. | Plan |
| Backend location | top-level `backend/` | Matches `repo-shape`'s "two top-level packages" monorepo shape. | Plan |
| Postgres/SQLAlchemy scope | Dependency + devcontainer service only, no engine/migrations | `backend-stack` explicitly defers that integration path until outbox/tags/flashcards work starts. | Plan |
| Notion scope | Dependency + settings placeholder only, no adapter/port | Same "scaffolding only" scope as Postgres — first real adapter is a future change. | Plan |
| Auth in this bootstrap | None — no stub middleware | Mechanism is an explicit, still-open future decision in `repo-shape`; inventing one now risks rework. | Plan |
| Testing scope | Only `/health` + `Settings` loader get `#### Tests` | Only two units in this change have an observable contract to assert before the code exists (`references/tdd-ability.md`); everything else is scaffolding. | Plan |
| Python runtime in devcontainer | `uv`-provisioned, no separate Python feature | Avoids `uv` vs. devcontainer-Python-feature interpreter-management conflicts. | Plan |

## Scope

**In scope:** devcontainer Postgres + uv toolchain; `backend/` project scaffold (pyproject, dependencies, hexagonal directory tree); a runnable FastAPI skeleton with a validated settings loader and a `/health` endpoint.

**Out of scope:** auth mechanism/implementation; SQLAlchemy engine/models/Alembic migrations; Notion adapter/port; outbox/tags/flashcards logic; daemon process supervision (systemd/launchd); CI pipeline changes beyond the devcontainer build/sync.

## Architecture / Approach

Hexagonal package under `backend/src/backend/`: `domain/` (plain Python), `application/` (use-cases + port `Protocol`s), `adapters/http|db|notion/` (framework-facing edges, `db` and `notion` left as empty placeholders for now), `config/` (settings), `main.py` (composition root). Devcontainer moves from a single Dockerfile build to Docker Compose (`app` + `postgres` services) so Postgres is available from day one without wiring an engine yet.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Devcontainer — uv + Postgres | Compose-based devcontainer with a healthy Postgres service | `runArgs --env-file` is silently ignored under Compose — must move to `env_file:` or `GITHUB_PACKAGES_TOKEN`/ordo install breaks quietly |
| 2. Backend scaffolding | `uv`-managed `backend/` project, hexagonal dirs, dependencies installed | `pydantic-ai-slim`'s `pydantic>=2.12` floor conflicting with an accidental explicit pin elsewhere |
| 3. Bootstrap contract — stubs | `Settings` field shape + `/health` route registered, no real behavior | None significant — pure interface commitment |
| 4. Bootstrap contract — behavior | Real settings validation + real `/health` response, tests passing | None significant — small, well-scoped contract |

**Prerequisites:** none — first code in the repository.
**Estimated effort:** small (4 phases, no domain logic yet).

## Open Risks & Assumptions

- Assumes Postgres is only needed as a running service for future work, not yet connected to from this change's code.
- Assumes `pydantic-ai-slim[web]` extras aren't needed yet (no LLM call sites exist in this bootstrap) — plain `pydantic-ai-slim` is added as a dependency floor for later use.

## Success Criteria (Summary)

- `docker compose ps` shows `postgres` healthy after a devcontainer rebuild.
- `uv run pytest` passes in `backend/`.
- `curl localhost:8000/health` returns `200 {"status": "ok"}` after `uv run fastapi dev`.
