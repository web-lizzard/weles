# Integration Suite On Demand Implementation Plan

## Overview

Let a person run the integration suite, Postgres lane included, in CI for a commit of their choosing, and never on its own (FR-05). The run leaves a durable record attached to the commit it actually tested, so S-05's deploy gate can later ask one question about one SHA (FR-06).

Execution state lives in `todos.md`, sibling of this file.

## Current State Analysis

- `.github/workflows/pr-gate.yml` exists and S-01 is `done`: five blocking checks plus the advisory `backend-property` job run on every pull request and every push to `main`. The Postgres lane is deliberately absent from it and was assigned to this slice (`context/changes/deployment-pr-gate/plan.md`, "What We're NOT Doing").
- The backend test bootstrap is already hermetic (S-01 Phase 1). `backend/tests/conftest.py` derives `DATABASE_URL` from `TEST_DATABASE_URL` when that variable is set, so a CI job needs to set `TEST_DATABASE_URL` and nothing else.
- The work pr-gate does not run is exactly two commands: `pytest tests/integration` (86 collected) and `pytest tests/unit -m postgres` (108 of 742, the rest deselected).
- `backend/tests/integration/support/postgres.py` needs a role that may `DROP DATABASE`/`CREATE DATABASE`: `_recreate_database_and_migrate` rebuilds the test database per session, and the newer `unmigrated_engine` fixture creates and drops a second database (`<name>_unmigrated`) alongside it. The maintenance connection targets the `postgres` database, derived from the bootstrap's `DATABASE_URL`.
- `vector` is created by the migrations themselves — `backend/src/adapters/out/sqlalchemy/migrations/versions/2ce37af2f0f8_create_capture_tables.py:25` runs `CREATE EXTENSION IF NOT EXISTS vector`. The CI service therefore needs the extension *available* and a role that may create it, not a pre-seeded database.
- Local timing on the devcontainer: `pytest tests/integration` takes ~53s wall.
- Local runs currently report 3 failures in `tests/integration/postgres/test_schema_upgrade.py`. That file is untracked — it is S-04's (`deployment-neon-schema`) red half awaiting its own `/implement`. It exists on no committed ref, so a CI run of a commit does not collect it. On a committed ref the suite is green (83 passed).
- `.devcontainer/docker-compose.yml` runs `pgvector/pgvector:pg16` with a `weles` superuser and a `pg_isready` healthcheck. That is the shape CI mirrors.

## Desired End State

- A person opens the `integration` workflow in GitHub Actions, types a commit SHA (or a branch or tag), and runs it. The workflow checks out exactly that ref, starts a Postgres service that provides `vector`, and runs the two commands above.
- The workflow has no trigger other than `workflow_dispatch`. Nothing schedules it, no push or pull request starts it.
- When the run finishes, the tested commit carries a commit status with context `integration` — `success` or `failure`, linking to the run. A run that starts leaves `pending` on that commit first.
- `AGENTS.md` and `CLAUDE.md` say how to start the lane and that it never starts itself.

Verify by: dispatching against the branch head and against an older `main` SHA, and reading back `GET /repos/{owner}/{repo}/commits/{sha}/status` for each — the tested SHA carries `integration`, and the SHA of the branch holding the workflow file does not (unless they are the same commit).

### Key Discoveries:

- **A dispatch run's `head_sha` is not the tested commit.** `workflow_dispatch` resolves the workflow file from the branch chosen in the UI, and the run is recorded against that branch's head. Checking out `inputs.ref` changes what the job tests, not what the run is filed under. This is why FR-06's record is a commit status published on a separately resolved SHA rather than a lookup over workflow runs.
- `backend/tests/conftest.py` (S-01 Phase 1) — `DATABASE_URL` is derived from `TEST_DATABASE_URL`; setting both in CI would be redundant and setting only `DATABASE_URL` would be wrong.
- `backend/tests/integration/support/postgres.py:15-43` — the maintenance database name comes from `DATABASE_URL`, which the bootstrap sets to the `postgres` database on the same host. That database always exists in the official image regardless of `POSTGRES_DB`.
- The official Postgres entrypoint creates the `POSTGRES_USER` role as a superuser, which is what makes `CREATE EXTENSION vector` and the per-session database rebuild work without extra grants.
- `job.status` is readable from a step in the same job, so a final `if: always()` step can map the job outcome onto a commit status state.
- `.github/rulesets/main.json` (S-01 Phase 4) lists required contexts by name. `integration` must stay out of it — a context that is only ever published on demand would leave every pull request waiting for a status that never arrives (the same trap as `path-filter-vs-required` in the frame log).

## What We're NOT Doing

- Adding `integration` to the ruleset's required checks, or to `pr-gate.yml`.
- Any automatic trigger: no schedule, no push, no pull request, no comment command.
- The deploy gate that reads this status. It belongs to S-05 (`deployment-manual-deploy`); this slice only produces the record it will read.
- Running the suite against a Neon branch. The test helper rebuilds databases wholesale, which a hosted Neon branch does not fit; the vendor-parity question stays open for S-05.
- Re-running the blocking checks. Those already ran on the commit through `pr-gate`.
- A mutation lane in CI.
- Fixing or waiting on S-04's in-flight `test_schema_upgrade.py`.

## Implementation Approach

One new workflow file, built in two passes. The first pass makes the lane runnable and provable: dispatch, checkout of the chosen ref, a Postgres service, the two commands. The second pass makes it *legible to a later machine reader*: resolve the ref to a full SHA once, and bracket the suite with a commit status on that SHA. Splitting it this way means the Postgres service is proven green before any status-publishing logic is layered on top, so a red second pass can only be a status bug. Documentation lands last, once the context name it quotes is real.

The change is developed on a branch and merged through the S-01 gate like any other.

## Critical Implementation Details

The final status step must run under `if: always()`, or a failing suite leaves the commit stuck at `pending` forever — which S-05 would read as "not yet run" rather than "failed". Map any non-`success` job status to `failure`; a cancelled run is not a passing one, and `cancelled` is not a valid commit-status state.

---

## Phase 1: On-Demand Integration Workflow

### Overview

The integration suite, Postgres lane included, runs in CI for a commit a person names, and starts by no other means.

### Changes Required:

#### 1. Integration workflow

**File**: `.github/workflows/integration.yml`

**Intent**: Give FR-05 its mechanism — a manually started run, against a chosen ref, with a Postgres that provides `vector`.

**Contract**:
- Workflow `name: integration`. Exactly one trigger: `workflow_dispatch`, with a required string input `ref` described as a commit SHA, branch, or tag.
- `permissions: contents: read`. A `concurrency` group keyed on the workflow and the input ref, without `cancel-in-progress`.
- One job `backend-integration` (`name: backend-integration`) on `ubuntu-latest`, `defaults.run.working-directory: backend`, with a `timeout-minutes` bound comfortably above the ~1 min local wall time.
- `services.postgres`: image `pgvector/pgvector:pg16`, `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` mirroring the devcontainer, port 5432 published to the runner, and `--health-cmd "pg_isready …"` options so the job waits for readiness.
- Job `env` carries `TEST_DATABASE_URL` only, pointing at `127.0.0.1:5432` with a database name distinct from `POSTGRES_DB`. `DATABASE_URL` is never set — the test bootstrap derives it.
- Steps: `actions/checkout@v6` with `ref: ${{ inputs.ref }}`; `astral-sh/setup-uv@v10.1.0` (`working-directory: backend`, cache enabled); `uv sync --frozen`; then `uv run --frozen pytest tests/integration` and `uv run --frozen pytest tests/unit -m postgres` as two steps.

### Success Criteria:

#### Automated Verification:

- `uvx --from actionlint-py actionlint .github/workflows/integration.yml` reports no errors
- The workflow's only trigger key is `workflow_dispatch`: `uv run --with pyyaml python -c "import yaml; assert set(yaml.safe_load(open('.github/workflows/integration.yml'))[True]) == {'workflow_dispatch'}"` passes

#### Manual Verification:

- Push the branch, then in GitHub → Actions → `integration` → Run workflow, supply the branch head SHA: the job runs, Postgres comes up healthy, and both pytest steps pass
- Run it again supplying an older `main` SHA: the job checks out that commit and passes, proving "any commit" rather than "the branch head"
- Confirm no `integration` run appears from the branch push itself or from opening the pull request

---

## Phase 2: Commit Status on the Tested SHA

### Overview

Every run leaves a `success` or `failure` verdict on the commit it actually tested, so a later reader can gate on one SHA.

### Changes Required:

#### 1. Resolved SHA and bracketing statuses

**File**: `.github/workflows/integration.yml`

**Intent**: Publish the record FR-06 depends on, against the resolved commit rather than the run's own `head_sha`.

**Contract**:
- `permissions` gains `statuses: write`.
- A step immediately after checkout resolves the checked-out commit to a full SHA and exposes it as a step output.
- A step before the suite publishes state `pending` on that SHA with context `integration`, and a final step with `if: always()` publishes `success` when `job.status` is `success` and `failure` otherwise. Both carry a `target_url` pointing at this run and a short `description`.
- Both statuses are posted with the `gh` CLI against `POST /repos/{owner}/{repo}/statuses/{sha}`, authenticated by the job's own `GITHUB_TOKEN`; no personal token and no other secret.
- The context string `integration` appears nowhere else in `.github/` — it is this slice's contract with S-05.

### Success Criteria:

#### Automated Verification:

- `uvx --from actionlint-py actionlint .github/workflows/integration.yml` reports no errors
- The final status step is unconditional on outcome: `grep -A2 'if: always()' .github/workflows/integration.yml` shows the status-publishing step

#### Manual Verification:

- Dispatch against a commit, then `gh api repos/{owner}/{repo}/commits/<tested-sha>/status --jq '.statuses[] | {context, state, target_url}'` shows `integration` at `success` linking to the run
- While that run is in flight, the same command shows `pending`
- Dispatch against a commit whose suite is red (temporarily break a test on a throwaway branch and dispatch its SHA): the same command shows `failure`, not a stuck `pending`; delete the throwaway branch afterwards
- `gh api repos/{owner}/{repo}/commits/<branch-head-sha>/status` for the branch the workflow was launched *from* shows no `integration` status when that commit is not the tested one
- Open pull requests stay mergeable: the `integration` context is absent from `.github/rulesets/main.json`

---

## Phase 3: Record the Lane for People and Agents

### Overview

The repository says how to run the lane, that it never runs itself, and what the resulting status is called.

### Changes Required:

#### 1. Agent guides

**File**: `AGENTS.md`, `CLAUDE.md`

**Intent**: The integration lane is invisible in a pull request by design, so its existence has to be written down or nobody will run it before a deploy.

**Contract**: The `## Commands` section of both files (they are identical copies) gains one line: the integration suite, Postgres lane included, runs only through the `integration` workflow dispatched with a `ref`, and a finished run leaves an `integration` commit status on that ref. No instance, host, or credential is named.

### Success Criteria:

#### Automated Verification:

- Both guides carry the line and stay identical: `diff <(grep -n 'integration' AGENTS.md) <(grep -n 'integration' CLAUDE.md)` reports no difference
- `diff AGENTS.md CLAUDE.md` reports no difference

---

## Testing Strategy

### Unit Tests:

None. This change adds no production code — it is CI configuration and documentation, which `context/foundation/testing-conventions.md` does not route through a test lane.

### Integration Tests:

No new tests. The existing integration suite is the subject of this change, not its object; Phase 1's manual verification is what proves the lane.

### Manual Testing Steps:

1. Dispatch against the branch head and confirm both pytest steps pass with a healthy Postgres service.
2. Dispatch against an older `main` SHA and confirm the older tree is what ran.
3. Read the commit status back for the tested SHA at `pending`, then `success`.
4. Force a red run and confirm the status lands on `failure`.
5. Confirm nothing dispatches the workflow automatically.

## Performance Considerations

The suite is ~53s locally for `tests/integration`; the Postgres lane rebuilds its database once per session and truncates between tests. In CI, container pull and `uv sync` dominate, and the uv cache keyed on `uv.lock` keeps the second run short. Nothing here runs per pull request, so this lane adds no latency to ordinary work.

## Migration Notes

Once S-05 lands, a commit without a green `integration` status is not deployable. Dispatching this workflow becomes a deliberate step before every deploy. If the status context is ever renamed, S-05's gate must be updated in the same change — the name is the contract.

## References

- Effort frame: `context/efforts/deployment/frame.md` (FR-05, FR-06)
- Frame log: `context/efforts/deployment/frame-log.md` (`bdd-integration-manual`, `integration-vs-deploy-gate`, `path-filter-vs-required`)
- Roadmap slice: `context/efforts/deployment/roadmap.md` (S-02)
- Sibling plan: `context/changes/deployment-pr-gate/plan.md` (hermetic bootstrap, job shape, ruleset)
- `context/foundation/testing-conventions.md` (integration lane, `-m postgres` marker)
- `context/foundation/rules/contract-testing.md` (real adapters on a separate, non-blocking cadence)
- `context/efforts/deployment/research-pg-vector-support.md` (pgvector availability)
- GitHub REST, commit statuses: https://docs.github.com/en/rest/commits/statuses
- Service containers in GitHub Actions: https://docs.github.com/en/actions/using-containerized-services/about-service-containers
- `workflow_dispatch` inputs: https://docs.github.com/en/actions/reference/events-that-trigger-workflows#workflow_dispatch
