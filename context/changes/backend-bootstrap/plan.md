# Backend Bootstrap Implementation Plan

## Overview

Install and bootstrap the Python backend service decided in `context/adrs/backend-stack` and `context/adrs/repo-shape`: a FastAPI daemon, managed by `uv`, laid out as a hexagonal (ports-and-adapters) package at top-level `backend/`, with its full dependency set installed and a runnable skeleton — a health endpoint and a validated settings loader — so later changes (outbox, notes adapter, auth) build on a working foundation instead of starting from zero.

## Current State Analysis

The repository currently holds only `context/` planning artifacts and devcontainer/tooling config — no application code exists yet, in either Python or Node. The devcontainer is a single `build.dockerfile` setup (`.devcontainer/devcontainer.json` + `.devcontainer/Dockerfile`, Ubuntu base + Node 22 feature), with no Postgres and no Python runtime. `context/adrs/backend-stack/decision.md` fixes the framework/persistence stack; `context/adrs/repo-shape/decision.md` fixes the monorepo shape (Python backend daemon + future Node/Ink TUI, no shared code, backend as the sole HTTP entrypoint). Both ADRs are still `status: open` (not yet `done`) — this change is one `implements` step toward closing them, not the only one.

### Key Discoveries:

- `.devcontainer/devcontainer.json:3-9` uses `build:`, not `dockerComposeFile:` — adding Postgres requires migrating to Compose, which also means `runArgs: ["--env-file", ...]` (`.devcontainer/devcontainer.json:25-28`) must move to Compose's `env_file:`, or the `GITHUB_PACKAGES_TOKEN` used by `post-create.d/08-install-ordo.sh` silently stops reaching the container (Compose ignores `runArgs` — microsoft/vscode-remote-release#4124).
- `post-create.d/` runs numbered scripts in sorted order (`.devcontainer/post-create.sh`); a new `uv sync` step slots in as another numbered script, after Postgres exists but does not need to wait on it (no DB connection is made in this change).
- ADR `backend-stack` explicitly defers async worker/outbox mechanics and leaves the Postgres integration path (Alembic, `pgvector`) "untested until the outbox/tags/flashcards work starts" — this change adds that dependency surface without building on top of it yet.
- ADR `repo-shape` defers the auth mechanism to a future decision; this change must not invent one.
- `pydantic-ai-slim`'s current release floors `pydantic>=2.12` — the backend's own `pyproject.toml` must not hand-pin an older Pydantic, or `uv`'s resolver conflicts against that floor.

## Desired End State

A developer can rebuild the devcontainer, get a healthy Postgres instance alongside the app container, run `uv sync` inside `backend/`, start the daemon with `uv run fastapi dev`, and `curl localhost:8000/health` to get back `200 {"status": "ok"}`. The package layout already separates domain/application/adapters so the next change (whichever ADR-driven capability comes first — notes adapter, outbox, or auth) has a boundary to slot into rather than one to invent.

Verification: `docker compose ps` shows `postgres` healthy; `uv run pytest` passes in `backend/`; `curl localhost:8000/health` returns `200 {"status": "ok"}`.

### Key Discoveries:

- No prior Python code exists, so there is no legacy layout or dependency set to reconcile against — this is a from-scratch scaffold, not a migration.

## What We're NOT Doing

- No auth mechanism or middleware — not even a stub gate. Endpoints stay open; the mechanism is a future decision per ADR `repo-shape`.
- No SQLAlchemy engine, session factory, declarative models, Alembic config, or migrations — `sqlalchemy[asyncio]`, `asyncpg`, and `alembic` are added as dependencies only.
- No Notion adapter or port definition — `notion-client` is added as a dependency only, with a settings placeholder for its token.
- No outbox, tag vocabulary, flashcard, or session logic (still open threads in `overview-thougts`, deferred by `backend-stack`).
- No daemon process supervision (systemd/launchd unit, or the TUI spawning it) — out of scope per `repo-shape`'s own deferral.
- No CI pipeline changes beyond what the devcontainer needs to build and sync.

## Implementation Approach

Order phases so each one's manual verification is actually checkable with what came before: the devcontainer (uv + Postgres) has to exist before a `uv`-managed project can be scaffolded inside it, and the project skeleton has to exist before there's anywhere to put a settings module or a route. The one genuinely TDD'able surface in this change — the settings loader's validation contract and the health endpoint's response contract — is split stub-then-behavior per `references/tdd-ability.md`: the stub phase commits the field names, types, and route shape (so tests have something concrete to import and call), the behavior phase wires real `pydantic-settings` env-loading and the real handler body, written to satisfy tests authored against the stub.

## Phase 1: Devcontainer — add uv and Postgres

### Overview

Give the devcontainer a Python toolchain (via `uv`, not a separate Python feature) and a Postgres instance to develop against, without breaking the existing `ordo`/`GITHUB_PACKAGES_TOKEN` install flow.

### Changes Required:

#### 1. Dockerfile — add `uv`

**File**: `.devcontainer/Dockerfile`

**Intent**: Make `uv` available in the container image so it can provision its own Python interpreter — no `ghcr.io/devcontainers/features/python` feature, which fights `uv`'s own interpreter management (astral-sh/uv#12197).

**Contract**: Adds `COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /usr/local/bin/` after the existing zsh/user setup, before the `ENV PATH` line.

#### 2. Compose file — Postgres service

**File**: `.devcontainer/docker-compose.yml` (new)

**Intent**: Add a Postgres service alongside the existing app container, with a named volume for persistence and a healthcheck so nothing races an unready DB.

**Contract**: Two services, `app` (built from `.devcontainer/Dockerfile`, context `..`) and `postgres` (`postgres:16`, named volume `postgres-data`, `pg_isready` healthcheck). `app` depends on `postgres` with `condition: service_healthy`.

```yaml
services:
  app:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile
    init: true
    env_file:
      - devcontainer.env
    environment:
      DATABASE_URL: postgresql+asyncpg://weles:weles@postgres:5432/weles
    volumes:
      - ..:/workspaces/weles:cached
    command: sleep infinity
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: weles
      POSTGRES_PASSWORD: weles
      POSTGRES_DB: weles
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U weles -d weles"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres-data:
```

#### 3. devcontainer.json — switch to Compose

**File**: `.devcontainer/devcontainer.json`

**Intent**: Point the devcontainer at the new Compose file instead of building the Dockerfile directly, and carry over the pieces Compose mode doesn't infer automatically.

**Contract**: Replace `"build": {"dockerfile": "Dockerfile"}` with `"dockerComposeFile": "docker-compose.yml"` and `"service": "app"`; add explicit `"workspaceFolder": "/workspaces/weles"`; remove the top-level `runArgs` block (superseded by the compose service's `env_file:`). `features`, `remoteUser`, `customizations`, `mounts`, `containerEnv`, `initializeCommand`, and `postCreateCommand` stay as-is.

#### 4. Env documentation

**File**: `.env.example`

**Intent**: Document the connection string a developer (or a future adapter) will use to reach the devcontainer's Postgres.

**Contract**: Adds a `DATABASE_URL=postgresql+asyncpg://weles:weles@postgres:5432/weles` line with a one-line comment noting it's dev-only, not a secret.

### Success Criteria:

#### Automated Verification:
- None — infra/config change, no automated assertion path in this stack.

#### Manual Verification:
- Rebuild the devcontainer ("Dev Containers: Rebuild Container").
- `docker compose -f .devcontainer/docker-compose.yml ps` shows `postgres` as `healthy`.
- `ordo status` succeeds inside the rebuilt container, confirming `GITHUB_PACKAGES_TOKEN` still reaches it through the moved `env_file:`.

---

## Phase 2: Backend project scaffolding

### Overview

Create the `backend/` package: a `uv`-managed project with the full dependency set from `backend-stack`, laid out in a hexagonal directory structure, wired into the devcontainer's post-create flow.

### Changes Required:

#### 1. uv project init

**File**: `backend/pyproject.toml` (new)

**Intent**: Establish the backend as a `uv`-managed, non-distributable service project with runtime and dev dependency groups.

**Contract**: `uv init --no-package` inside `backend/`, `requires-python = ">=3.12"`. Runtime deps: `fastapi[standard]`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `notion-client`, `pydantic-ai-slim` — all as version-range floors (`>=`), not exact pins, per Astral's own FastAPI integration guide; `uv.lock` does the pinning. Dev deps via PEP 735 `[dependency-groups]`: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`. No explicit `pydantic` pin — it floats to satisfy both FastAPI's and `pydantic-ai-slim`'s floors.

#### 2. Hexagonal directory skeleton

**File**: `backend/src/backend/{domain,application,adapters/http,adapters/db,adapters/notion,config}/__init__.py`, `backend/tests/{unit,integration}/__init__.py`

**Intent**: Commit the ports-and-adapters boundary from `backend-stack` to the file tree before any real code exists, so the first domain/adapter code has an obvious home.

**Contract**: Empty (or near-empty) `__init__.py` per package: `domain/` (plain Python entities, no framework imports), `application/` (use-cases and port `Protocol`s), `adapters/http/` (FastAPI routers, request/response schemas — never domain or ORM types), `adapters/db/` and `adapters/notion/` (placeholders — no code, real adapters land in later changes), `config/` (settings module goes here in Phase 3).

#### 3. Composition root skeleton

**File**: `backend/src/backend/main.py` (new)

**Intent**: A bare FastAPI app object as the daemon's entrypoint, with no routes yet — routes and settings wiring land in Phases 3–4.

**Contract**: `app = FastAPI()`, no routes registered, no settings import yet.

#### 4. Devcontainer sync step

**File**: `.devcontainer/post-create.d/20-backend-sync.sh` (new)

**Intent**: Make the backend's dependencies installed automatically on container (re)creation, same as the existing `ordo`/pre-commit/Claude Code steps.

**Contract**: `cd backend && uv sync`, executable, following the numbering/sorted-order convention of the existing `post-create.d/` scripts.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv sync` exits 0.
- `cd backend && uv run python -c "import backend"` exits 0.

#### Manual Verification:
- None beyond the automated checks above — this phase is pure scaffolding.

---

## Phase 3: Bootstrap contract — stubs

### Overview

Commit the two symbols Phase 4's tests import: the `Settings` field shape and the `/health` route, both with placeholder bodies — no env-loading, no real response yet.

### Changes Required:

#### 1. Settings field shape

**File**: `backend/src/backend/config/settings.py` (new)

**Intent**: Fix the settings contract's field names and types ahead of wiring real env-loading, so Phase 4's tests can import a stable `Settings` symbol.

**Contract**: `Settings` class with `database_url: str` and `notion_api_token: str | None = None`, not yet inheriting `pydantic_settings.BaseSettings` — plain type declarations only, no env-file wiring.

#### 2. Health route stub

**File**: `backend/src/backend/adapters/http/health.py` (new), wired into `backend/src/backend/main.py`

**Intent**: Register the `/health` route's path and method ahead of a real handler body, so Phase 4's tests can call it.

**Contract**: `GET /health` registered on `app`, handler body a placeholder (`...`) that does not yet return a real response.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "from backend.config.settings import Settings"` exits 0.
- `cd backend && uv run python -c "from backend.main import app"` exits 0.

#### Manual Verification:
- None — stub phase, no observable behavior yet.

---

## Phase 4: Bootstrap contract — behavior

### Overview

Wire real behavior behind Phase 3's stubs: `Settings` becomes a validating `pydantic-settings` loader, `/health` returns a real response — and write the tests that prove both contracts.

### Changes Required:

#### 1. Settings — real env-loading

**File**: `backend/src/backend/config/settings.py`

**Intent**: Load required config from the environment/`.env`, failing loudly and testably when `database_url` is missing or malformed.

**Contract**: `Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")`; missing `database_url` raises `pydantic.ValidationError` at instantiation.

#### 2. Health — real response

**File**: `backend/src/backend/adapters/http/health.py`

**Intent**: Give the daemon a real liveness check a developer (or later, a process supervisor) can hit.

**Contract**: `GET /health` returns `200 {"status": "ok"}`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` passes, covering:
  - `GET /health` returns `200` with `{"status": "ok"}`, via `httpx.AsyncClient` + `ASGITransport(app=app)`.
  - Instantiating `Settings` with `database_url` unset (via `monkeypatch.delenv`) raises `pydantic.ValidationError`.

#### Manual Verification:
- `cd backend && uv run fastapi dev`, then `curl localhost:8000/health` returns `200 {"status": "ok"}`.

---

## Testing Strategy

### Unit Tests:
- `Settings` validation contract (Phase 4): raises on missing `database_url`.

### Integration Tests:
- `/health` endpoint contract (Phase 4): full ASGI request/response round-trip via `httpx.AsyncClient` + `ASGITransport`.

### Manual Testing Steps:
- Rebuild devcontainer, confirm Postgres healthy and `ordo status` still works (Phase 1).
- `uv sync` + import smoke-check (Phase 2).
- `uv run fastapi dev` + `curl localhost:8000/health` (Phase 4).

## Performance Considerations

None — no load-bearing code path exists yet; this change only bootstraps the project.

## Migration Notes

None — this is a from-scratch scaffold, not a migration of existing code or data.

## References

- `context/adrs/backend-stack/decision.md` — framework/persistence stack decision.
- `context/adrs/repo-shape/decision.md` — monorepo shape, TUI/backend boundary, auth deferral.
- `context/changes/backend-bootstrap/change.md` — this change's identity and scope note.
- [uv + FastAPI integration guide](https://docs.astral.sh/uv/guides/integration/fastapi/)
- [uv Docker integration guide](https://docs.astral.sh/uv/guides/integration/docker/)
- [ShahriyarR/hexagonal-fastapi-jobboard](https://github.com/ShahriyarR/hexagonal-fastapi-jobboard) — reference hexagonal layout
- [pydantic-settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [FastAPI async tests docs](https://fastapi.tiangolo.com/advanced/async-tests/)
- [Dev Containers spec — Docker Compose properties](https://containers.dev/implementors/json_reference/)
- [microsoft/vscode-remote-release#4124](https://github.com/microsoft/vscode-remote-release/issues/4124) — `runArgs` ignored under Compose
