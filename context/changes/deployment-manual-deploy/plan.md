# Manual Deploy to Mikrus Implementation Plan

## Overview

Slice S-05 of the `deployment` effort (FR-01, FR-06) is the tracer bullet for the production path. A backend image and its Postgres database run as a compose stack on the author's Mikrus VPS. The stack changes only when the author dispatches a deploy for a specific `main` commit, and the deploy refuses a commit unless its blocking checks and an integration run passed.

Execution state lives in `todos.md`, sibling of this file.

## Current State Analysis

- No production image, no deploy workflow, nothing on the VPS. The only Docker assets are the devcontainer's `.devcontainer/Dockerfile` and `docker-compose.yml`.
- `pr-gate.yml` runs five blocking jobs on pull requests and on pushes to `main`. `.github/rulesets/main.json` requires exactly those contexts.
- `integration.yml` is dispatch-only and publishes an `integration` commit status on the tested SHA.
- The S-04 script `backend/scripts/migrate_database.py` upgrades any direct Postgres URL. Its env var is `NEON_DIRECT_URL`, but it refuses only `-pooler` hosts.
- The app does not migrate on startup. `/health` never touches the database. The outbox worker starts in the lifespan and polls every second.
- The author owns a Mikrus 2.1 VPS (1 GB RAM, 10 GB SSD, LXC, no stable swap) and can add a data disk.

## Desired End State

The author runs the `deploy` workflow with a commit SHA.

- **Refusal:** a commit that is not on `main`, lacks a green required check, or lacks a successful `integration` status fails the `verify` job, and nothing on the VPS changes.
- **Deploy:** a passing commit's image is built on the runner and streamed to the VPS. `docker compose up --wait` replaces only the API container, with Postgres left running.
- **Failed deploy:** an API that never turns healthy is rolled back to the previously deployed SHA, and the job ends red.
- **Exposure:** both services listen on `127.0.0.1` only. The author reaches them through SSH tunnels: the TUI via `http://localhost:8000`, the S-04 script via `127.0.0.1:5432`.

Verify it by dispatching deploys that are refused, deployed, broken-and-restored, and rolled back, as listed in the phases.

### Key Discoveries:

- `backend/src/adapters/out/sqlalchemy/schema_upgrade.py:22-35`: `direct_asyncpg_url` accepts any `postgres`/`postgresql` URL and refuses only `-pooler` hosts. S-04 works unchanged against a tunnelled local database.
- `backend/src/adapters/out/sqlalchemy/migrations.py:10-12`: the Alembic config resolves next to the module file, so copying `src/` into the image is enough.
- `backend/src/config/settings.py:38-42`: `env_file=".env"` with `extra="forbid"`. The image must not contain a `.env`, and runtime config arrives as real environment variables.
- `backend/src/main.py:22-35`: the lifespan starts one outbox worker per process, so the image runs a single uvicorn worker.
- `tui/src/instance/address.ts:18-22`: the TUI accepts `http://` addresses, so `weles instance set http://localhost:8000` over a tunnel works.
- `.github/workflows/integration.yml:48-56,63-75`: the `integration` status context and the `gh api` pattern the gate reads back.
- `research.md:41` (this change): each idle outbox tick runs three light `SKIP LOCKED` claims. That load is trivial for a local Postgres, while on Neon free it would keep compute awake past 100 CU-hours a month.
- `context/efforts/deployment/research-mikrus-cli.md:30-32,52`: Mikrus has no Docker API and `exec` caps at 60 s. SSH/SCP is the supported path. GitHub-hosted runners have no outbound IPv6, so SSH goes over IPv4 to `srvXX.mikr.us` on port `10000 + machine number`, never 22.

## What We're NOT Doing

- Neon for the hosted instance: the author chose a self-hosted `pgvector` container, a deviation from the effort frame (see Migration Notes).
- A public address, reverse proxy, TLS, or `--proxy-headers` (S-08).
- A registry. The image is never published.
- Running migrations inside the deploy, or guarding deploy/schema ordering (frame out of scope; S-04 runbook order stands).
- Automated backups. The runbook gives a manual `pg_dump`.
- Error tracking (S-06), diagnostics skill (S-07), a non-root deploy user, and a database-aware health check.
- Renaming `NEON_DIRECT_URL`.
- A Mikrus 3.0 upgrade. It is an escalation path only (Performance Considerations).

## Implementation Approach

Four phases, each checkable on its own:

1. An image that runs locally.
2. A gate job that refuses bad SHAs before anything touches the VPS.
3. A one-time host bootstrap, done by the author from a committed runbook.
4. The deploy job and its compose stack.

Runtime secrets live only in files on the VPS. GitHub holds only SSH connection secrets in a `production` environment, so the public repository names no instance. None of the phases has a pre-code observable outcome to assert (Dockerfile, CI wiring, docs, deploy script), so none carries a `#### Tests` row.

## Critical Implementation Details

- **Health.** `docker compose up --wait` treats a service without a healthcheck as ready once it starts. Both services need a healthcheck, or a crashing API reads as a successful deploy. `python:3.12-slim` has no `curl`, so the API healthcheck uses `python -c` with `urllib`.
- **First deploy.** The first deploy runs against an empty database, and the outbox worker errors until S-04 migrates it. The runbook migrates right after the first deploy, then runs `docker compose restart api`.

## Phase 1: Production Backend Image

### Overview

A lean, non-root backend image that starts the API from environment variables alone.

### Changes Required:

#### 1. Image definition

**File**: `backend/Dockerfile`

**Intent**: Build the API image on a CI runner, never on the VPS. Dependencies come from the lockfile, without dev tools.

**Contract**:

- Base: `python:3.12-slim`, with `uv` copied from `ghcr.io/astral-sh/uv:0.9.6`, the same pin as the devcontainer.
- Dependencies: `uv sync --frozen --no-dev` into `/app/.venv`, then `src/` copied in.
- Runtime: a non-root user and `EXPOSE 8000`. The command is `uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000 --workers 1`.

#### 2. Build context filter

**File**: `backend/.dockerignore`

**Intent**: Keep secrets, local environments, and test and mutation artifacts out of the build context and the image.

**Contract**: Excludes at least `.env`, `.env.*`, `.venv`, `tests`, `mutants`, `.mutmut-cache`, `__pycache__`, `.pytest_cache`, `.ruff_cache`.

### Success Criteria:

#### Automated Verification:

- `backend/.dockerignore` excludes `.env`, `.venv`, `tests`, and `mutants`
- `backend/Dockerfile` sets a non-root `USER` and runs uvicorn with `--workers 1`

#### Manual Verification:

- On a machine with Docker: `docker build -t weles-api:local backend` succeeds, and the image contains no `/app/.env`.
- `docker run --rm -p 127.0.0.1:8000:8000 -e DATABASE_URL=… -e AUTH_SIGNING_SECRET=… -e TRACING_ENABLED=false weles-api:local`, then `curl -fsS http://127.0.0.1:8000/health` returns `{"status":"ok"}`.

---

## Phase 2: Deploy Gate

### Overview

A dispatch-only `deploy` workflow whose `verify` job enforces FR-01 and FR-06 before any VPS access.

### Changes Required:

#### 1. Gate workflow

**File**: `.github/workflows/deploy.yml`

**Intent**: Refuse any SHA that is not on `main`, or whose required checks or integration run did not pass. Print exactly what is missing.

**Contract**:

- **Trigger:** `on: workflow_dispatch` only, with a required string input `sha`.
- **Workflow settings:** `concurrency: { group: deploy, cancel-in-progress: false }` and `permissions: { contents: read, checks: read, statuses: read }`.
- **Job `verify`** steps, in order:
  1. Checkout `main` with full history.
  2. Resolve the input to a full commit SHA, failing on an unknown ref.
  3. `git merge-base --is-ancestor <sha> origin/main`.
  4. Read required contexts from `.github/rulesets/main.json`: `.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context`.
  5. For each context, require the latest check run of that name on the SHA (`gh api repos/{repo}/commits/{sha}/check-runs --paginate`) to be `completed` with conclusion `success`.
  6. Require the newest `integration` entry in `gh api repos/{repo}/commits/{sha}/statuses` to be `success`.
  7. Collect every failure, print them all, then exit non-zero.
- **Output:** the resolved `sha`, for Phase 4's job.

### Success Criteria:

#### Automated Verification:

- `uvx --from actionlint-py actionlint .github/workflows/deploy.yml` reports no errors
- `workflow_dispatch` is the only trigger key in `deploy.yml`

#### Manual Verification:

- The check-run names on the current `main` head match every context in `.github/rulesets/main.json`.
- Dispatching with a SHA that is not on `main` fails `verify` and names the ancestry failure.
- Dispatching with a `main` SHA that has no `integration` status fails `verify` and names the missing integration run.
- Dispatching with a `main` SHA that has green checks and a successful `integration` run passes `verify`.
- Pushing to `main` starts no `deploy` run.

---

## Phase 3: Mikrus Host Bootstrap and Runbook

### Overview

The author prepares the VPS once from a committed runbook, which also records the deploy, migrate, rollback, backup, and access procedures.

### Changes Required:

#### 1. Hosting runbook

**File**: `README.md`

**Intent**: A new "Hosting on Mikrus" section that a first-time Mikrus user can follow end to end. It names no instance.

**Contract**:

- **One-time setup:**
  - SSH login with a dedicated deploy key on port `10000 + machine number`, never port 22.
  - Docker Engine with the compose plugin (`docker compose version`).
  - The data disk mounted at `/srv/weles`, with `/srv/weles/pgdata` created.
  - `/srv/weles/postgres.env` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) and `/srv/weles/backend.env` (`DATABASE_URL=postgresql+asyncpg://…@postgres:5432/…`, `AUTH_SIGNING_SECRET`, `ENVIRONMENT_NAME=prod`, `OPENROUTER_API_KEY`, Langfuse keys), both `chmod 600`.
  - `docker pull pgvector/pgvector:pg16`.
  - A GitHub environment `production` holding `DEPLOY_SSH_HOST`, `DEPLOY_SSH_PORT`, `DEPLOY_SSH_USER`, `DEPLOY_SSH_KEY`, and `DEPLOY_SSH_KNOWN_HOSTS` (from `ssh-keyscan -p <port> <host>`).
- **Deploy:** dispatch integration for the SHA, then dispatch `deploy` with the same SHA.
- **Migrate:** open `ssh -L 5432:127.0.0.1:5432`, then run S-04 from a checkout of the SHA with `NEON_DIRECT_URL=postgresql://…@127.0.0.1:5432/<db>`. On a first deploy, follow it with `docker compose -f /srv/weles/compose.yml restart api`.
- **Access:** open `ssh -L 8000:127.0.0.1:8000`, then `weles instance set http://localhost:8000`.
- **Rollback:** dispatch `deploy` with an older gated SHA.
- **Backup:** `docker compose -f /srv/weles/compose.yml exec postgres pg_dump -U <user> <db> > backup.sql` over SSH.
- **Resources:** `docker stats --no-stream` and `free -m`, with the Mikrus 3.0 escalation signal.

The existing Neon section is reworded to "hosted database". It keeps its steps and adds the tunnel URL form.

#### 2. Agent guides

**File**: `CLAUDE.md`, `AGENTS.md`

**Intent**: Agents learn that deploys happen only through the dispatched `deploy` workflow for a gated `main` SHA.

**Contract**: One line under `## Commands` in both files, which stay identical.

### Success Criteria:

#### Automated Verification:

- `README.md` has a "Hosting on Mikrus" section and names no host, IP, or machine number
- Both agent guides carry the deploy line and remain identical

#### Manual Verification:

- `ssh -p <10000+nr> -i <deploy key> <user>@<host> true` succeeds without a password prompt.
- On the VPS, `docker compose version` prints a v2 version, and `df -h /srv/weles` shows the added disk.
- `ls -l /srv/weles/*.env` shows both files as `-rw-------`.
- `docker pull pgvector/pgvector:pg16` completes on the VPS.
- The `production` environment lists all five `DEPLOY_SSH_*` secrets.

---

## Phase 4: Ship to Mikrus

### Overview

The `deploy` job streams the gated image to the VPS and switches the API through compose. It restores the previous SHA when the new API never turns healthy.

### Changes Required:

#### 1. Host stack

**File**: `deploy/compose.yml`

**Intent**: Declare the two-service runtime once: network, volume, health, start order, memory-conscious Postgres, and bounded logs.

**Contract**:

- **Project:** `name: weles`.
- **Service `postgres`:**
  - Image `pgvector/pgvector:pg16`, with `env_file: /srv/weles/postgres.env`.
  - Volume `/srv/weles/pgdata:/var/lib/postgresql/data`, published on `127.0.0.1:5432:5432`.
  - Command flags `-c shared_buffers=96MB -c max_connections=20 -c work_mem=4MB -c maintenance_work_mem=64MB -c effective_cache_size=256MB`.
  - Healthcheck `pg_isready`, `restart: unless-stopped`.
- **Service `api`:**
  - Image `weles-api:${WELES_API_TAG:?}`, with `env_file: /srv/weles/backend.env`, published on `127.0.0.1:8000:8000`.
  - `depends_on: postgres: condition: service_healthy`, healthcheck via `python -c` fetching `http://127.0.0.1:8000/health`, `restart: unless-stopped`.
- **Both services:** `json-file` logging with `max-size: 10m`, `max-file: 3`.

#### 2. Remote switch script

**File**: `deploy/remote-deploy.sh`

**Intent**: Switch the API to the given SHA on the VPS, restore the previous SHA on failure, and keep the disk from filling.

**Contract**: `remote-deploy.sh <sha>`, run from `/srv/weles` with `set -euo pipefail`.

1. Read `previous` from `/srv/weles/deployed_sha` (may be absent).
2. `WELES_API_TAG=<sha> docker compose -f /srv/weles/compose.yml up -d --wait --wait-timeout 120`.
3. On success, write `<sha>` to `deployed_sha` and remove every `weles-api` image tag other than `<sha>` and `previous`.
4. On failure, if `previous` exists, re-run `up -d --wait` with `previous`. Exit non-zero either way.

#### 3. Deploy job

**File**: `.github/workflows/deploy.yml`

**Intent**: After `verify` passes, build the image for that exact SHA, ship it without a registry, and run the switch.

**Contract**:

- **Job `deploy`:** `needs: verify`, `environment: production`.
- **Steps:**
  1. Checkout `needs.verify.outputs.sha`.
  2. `docker build -t weles-api:<sha> backend`.
  3. Write `DEPLOY_SSH_KEY` and `DEPLOY_SSH_KNOWN_HOSTS` into `~/.ssh`.
  4. `docker save weles-api:<sha> | gzip | ssh -p $DEPLOY_SSH_PORT $DEPLOY_SSH_USER@$DEPLOY_SSH_HOST 'gunzip | docker load'`.
  5. `scp -P` `deploy/compose.yml` and `deploy/remote-deploy.sh` to `/srv/weles/`.
  6. `ssh … bash /srv/weles/remote-deploy.sh <sha>`.
  7. Append the deployed SHA and its outcome to `$GITHUB_STEP_SUMMARY`.
- **Secrets:** no SSH secret value is echoed.

### Success Criteria:

#### Automated Verification:

- `uvx --from actionlint-py actionlint .github/workflows/deploy.yml` reports no errors
- `uvx --from shellcheck-py shellcheck deploy/remote-deploy.sh` reports no findings
- The `deploy` job declares `needs: verify` and `environment: production`

#### Manual Verification:

- **First deploy:** dispatching `deploy` for a gated SHA ends green, and `docker compose -f /srv/weles/compose.yml ps` shows `postgres` and `api` healthy.
- **Local-only ports:** `ss -ltnp` on the VPS shows ports 8000 and 5432 bound to `127.0.0.1` only.
- **Working instance:** after migrating through the tunnel and restarting `api`, the TUI at `http://localhost:8000` can sign in and complete a capture.
- **Resources:** `docker stats --no-stream` and `free -m` on the VPS show both containers running with free memory left. Record the figures in the change notes.
- **Broken deploy restores:** with `DATABASE_URL` commented out in `backend.env`, dispatching `deploy` ends red and `deployed_sha` still names the previous SHA, with `api` healthy on it. Restore `backend.env` afterwards.
- **Rollback:** dispatching `deploy` for an older gated SHA switches `api` to that SHA, and `docker images weles-api` lists at most two tags.

---

## Testing Strategy

### Unit Tests:

None. No production code changes.

### Integration Tests:

None added. The deploy gate consumes the existing `integration` run.

### Manual Testing Steps:

1. Build and run the image locally (Phase 1).
2. Walk the gate's refusal and pass paths (Phase 2).
3. Bootstrap the VPS from the runbook (Phase 3).
4. First deploy, migrate, TUI over the tunnel, resource snapshot, broken-deploy restore, rollback (Phase 4).

## Performance Considerations

- **Mikrus 2.1 memory:** one uvicorn worker (~150–250 MB estimated), a trimmed Postgres (~100–200 MB), and Docker plus the system should fit in 1 GB. With no swap, an OOM kills a process instead of slowing it. `restart: unless-stopped` recovers it, and an in-flight request is lost.
- **Escalation to Mikrus 3.0:** when `docker inspect` shows `OOMKilled`, or container restart counts climb.
- **Disk:** at most two API image tags, the `pgvector` image, and capped JSON logs stay well within 10 GB. Database files live on the added disk.

## Migration Notes

- **Schema ordering:** unchanged from S-04. Run the migration from a checkout of the SHA, over the tunnel, before deploying a commit that adds revisions.
- **Frame deviation:** the effort frame, roadmap S-05 text, and effort `research.md` assume Neon. This plan deliberately hosts Postgres on the VPS, which is the author's decision during planning and grounded in this change's `research.md`. The effort frame and roadmap need a follow-up amendment, which `/plan` does not make.

## References

- Effort frame: `context/efforts/deployment/frame.md` (FR-01, FR-06, boundaries)
- Roadmap slice: `context/efforts/deployment/roadmap.md` (S-05)
- Research: `context/changes/deployment-manual-deploy/research.md`, `context/efforts/deployment/research.md`, `context/efforts/deployment/research-mikrus-cli.md`
- Prior slices: `context/archive/changes/2026-09-14-deployment-pr-gate/`, `context/archive/changes/2026-09-14-deployment-neon-schema/`, `context/changes/deployment-integration-on-demand/`
