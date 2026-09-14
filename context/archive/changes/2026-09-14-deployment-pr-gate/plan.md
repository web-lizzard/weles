# Deployment PR Gate Implementation Plan

## Overview

Make `main` accept a change only through a pull request whose blocking checks passed (FR-03), and run property hunts on the same pull request as a visible, non-blocking job (FR-04). Today the repository has no `.github/`, commits land directly on `main`, and the backend suites cannot even collect in a clean checkout, so no check could gate anything yet.

Execution state lives in `todos.md`, sibling of this file.

## Current State Analysis

- No `.github/` directory, no workflows, no branch protection. Commits land directly on `main` (`git log`).
- The backend suites are not hermetic. `backend/src/adapters/compose.py:82` builds `Settings()` at import time, and `Settings` requires `database_url` and `auth_signing_secret` (`backend/src/config/settings.py`). Locally they come from the gitignored `backend/.env` and the devcontainer environment. In a clean checkout of `468537c`:
  - `pytest tests/unit` fails at collection (`database_url` missing).
  - `pytest tests/bdd` fails at import (`auth_signing_secret` missing), then on `OPENROUTER_API_KEY` once the other two are supplied.
  - `backend/tests/conftest.py:17-27` already sets offline defaults, but inside `pytest_configure`, which runs after `pytest_plugins` (and through them `adapters.compose`) are imported. That is too late.
- With `DATABASE_URL`, `AUTH_SIGNING_SECRET`, and `OPENROUTER_API_KEY` placeholders in the environment, a clean checkout is green: unit `-m "not postgres"` 630 passed, BDD 57 passed (~63s), property 33 passed (~6s).
- `tests/unit` holds 108 contract cases parametrized `[postgres]` that call `pytest.fail` without `TEST_DATABASE_URL` (`backend/tests/integration/support/postgres.py:15-21`).
- `backend/tests/integration/support/postgres.py:15-43` derives both the test database URL and the maintenance database from `DATABASE_URL` whenever that variable is present, so a placeholder `DATABASE_URL` must not point at an unrelated host or database.
- TUI in a clean checkout with a CI-like environment: `pnpm test` 313 passed, `pnpm typecheck` clean, `biome ci` clean. The 4 local failures come from the devcontainer's `FORCE_COLOR=3`, which runners do not set.
- Static checks at `468537c`: `ruff check` clean, `ruff format --check` clean, `basedpyright` 0 errors.
- Toolchain: uv 0.9.6, `backend/.python-version` 3.12, Node 22, `tui/package.json` pins `packageManager: pnpm@11.24.0`, lockfiles committed (`backend/uv.lock`, `tui/pnpm-lock.yaml`).

## Desired End State

- Every pull request to `main`, whatever it touches, runs five blocking checks: `backend-static`, `backend-unit`, `backend-bdd`, `tui-static`, `tui-unit`. The same checks run on every push to `main`, so each `main` commit carries its own results for S-05's deploy gate.
- The same workflow runs `backend-property`. A found counterexample turns it red on the pull request, and the pull request stays mergeable.
- An active ruleset on the default branch requires a pull request, the five checks from GitHub Actions, and an up-to-date branch. It forbids force-push and deletion, and nobody bypasses it. The ruleset's source of truth is committed at `.github/rulesets/main.json`.
- `cd backend && uv run pytest tests/unit -m "not postgres"` and `uv run pytest tests/bdd` pass in a fresh clone with no `.env` and no exported variables.

Verify by: a direct `git push origin main` is rejected; a pull request with a red required check cannot merge; a pull request whose only red check is `backend-property` can.

### Key Discoveries:

- `backend/src/adapters/compose.py:82` — import-time `Settings()` is the root cause of non-hermetic collection. Refactoring it is out of scope; the test bootstrap supplies placeholders instead.
- `backend/tests/conftest.py:10` — `pytest_plugins = ["integration.support.postgres"]` is loaded after the module body runs, so module-level `os.environ.setdefault` lands before any plugin import.
- `backend/tests/integration/support/postgres.py:22-42` — `DATABASE_URL`, when set, overrides the host of the test URL and names the maintenance database.
- `pnpm/setup@v2` is the pnpm-maintained action for pnpm 11+. It installs pnpm from `packageManager`, installs the requested runtime (`node@22`), caches the store, and runs `pnpm install` itself. `pnpm/action-setup` targets older pnpm.
- `astral-sh/setup-uv@v10` provides uv with cache keyed on `uv.lock`.
- GitHub Actions reports each job as a check run named after the job's `name`. Ruleset required checks address it by `context` plus `integration_id` 15368 (GitHub Actions).
- Required checks skipped by path filters block merging ("Waiting for status to be reported"), which is why no path filters are used (frame-log `path-filter-vs-required`).

## What We're NOT Doing

- Path-scoped runs. Every blocking check runs on every pull request (frame out-of-scope).
- The integration suite and the `[postgres]` contract cases. They belong to S-02 (`deployment-integration-on-demand`), on demand.
- Image builds, publishing, deploys, or deploy gating (S-03, S-05).
- A mutation lane in CI (advisory, local).
- Refactoring `adapters/compose.py` to build settings lazily.
- A drift check between the backend OpenAPI schema and `tui/src/api/generated/schema.d.ts`.
- Pinning actions to commit SHAs or adding Dependabot. Actions are pinned to major tags.
- Committing the author's pending working-tree changes (see Prerequisites).

## Implementation Approach

Make the suites hermetic first, so CI needs no secrets or placeholder environment at all and local clean clones behave the same way. Then add one workflow file carrying the five blocking jobs, followed by the advisory property job in the same file. Protection comes last: a committed ruleset JSON applied once through GitHub, plus a one-line workflow rule in the agent guides.

The change itself is implemented on a branch (`deployment-pr-gate`) and reaches `main` through a pull request. That pull request is the first real run of the gate, and the ruleset is applied before it merges, so this change is the first one to pass through it.

**Prerequisites:** the author's uncommitted `pydantic-ai-slim[openai]` dependency change (`backend/pyproject.toml`, `backend/uv.lock`) must be on `main` before the first pull request runs. Without it `backend-bdd` fails at import with "Please install `openai`". The uncommitted `distill_model` default change in `backend/src/config/settings.py` must land together with its `test_settings_defaults_distill_model_when_unset` update, or be reverted.

## Critical Implementation Details

The `DATABASE_URL` placeholder must be derived from `TEST_DATABASE_URL` when that variable is set: the same URL with the database swapped to `postgres`. A fixed placeholder would redirect the Postgres helper's test and maintenance connections to a non-existent host the moment S-02 sets only `TEST_DATABASE_URL`.

Required-check contexts are matched by name. The job `name` values in the workflow and the `context` values in the ruleset must be identical strings, and no other workflow may reuse them.

---

## Phase 1: Hermetic Backend Test Bootstrap

### Overview

Backend unit and BDD suites collect and pass in a clean checkout with no `.env` and no exported configuration, by supplying offline placeholders before any plugin imports production composition.

### Changes Required:

#### 1. Repository-wide pytest bootstrap

**File**: `backend/tests/conftest.py`

**Intent**: Move the offline defaults out of `pytest_configure` to module level, and add the three settings a clean checkout lacks, so `adapters.compose`'s import-time `Settings()` succeeds without touching production code.

**Contract**: At module import, before `pytest_plugins` loads, `os.environ.setdefault` is applied for:
- `EMBEDDING_PROVIDER`, `CAPTURE_AGENT_PROVIDER`, `DISTILL_TASK_PROVIDER`, `TRACING_ENABLED`, `AUTH_SIGNING_SECRET` (existing values, moved)
- `OPENROUTER_API_KEY` (non-functional placeholder)
- `DATABASE_URL` (derived as below)

Values already present in the environment always win. `pytest_configure` no longer sets environment variables. `pytest_ignore_collect` is unchanged.

```python
_test_database_url = os.environ.get("TEST_DATABASE_URL")
_ = os.environ.setdefault(
    "DATABASE_URL",
    make_url(_test_database_url)
    .set(database="postgres")
    .render_as_string(hide_password=False)
    if _test_database_url
    else "postgresql+asyncpg://placeholder:placeholder@127.0.0.1:1/placeholder",
)
```

### Success Criteria:

#### Automated Verification:

- In a fresh `git worktree add` of the phase commit (no `backend/.env`), with `DATABASE_URL`, `TEST_DATABASE_URL`, `AUTH_SIGNING_SECRET`, `OPENROUTER_API_KEY` unset: `cd backend && uv sync --frozen && uv run --frozen pytest tests/unit -m "not postgres"` passes
- Same worktree and environment: `uv run --frozen pytest tests/bdd` passes
- `cd backend && env -u DATABASE_URL uv run pytest tests/unit -m postgres` passes against the devcontainer `TEST_DATABASE_URL` (derived placeholder keeps the Postgres helper working)
- `cd backend && uv run ruff check . && uv run ruff format --check . && uv run basedpyright` clean

---

## Phase 2: Blocking Checks Workflow

### Overview

Every pull request to `main` and every push to `main` runs the five blocking checks, with no secrets and no job environment.

### Changes Required:

#### 1. PR gate workflow

**File**: `.github/workflows/pr-gate.yml`

**Intent**: One workflow that runs the backend and TUI suites plus their static checks on every pull request, whatever it touches, and on `main` pushes so merged commits carry results.

**Contract**:
- Workflow `name: pr-gate`. Triggers: `pull_request` with `branches: [main]`, and `push` with `branches: [main]`. No `paths` filters.
- `permissions: contents: read`. A `concurrency` group keyed on workflow and ref, with `cancel-in-progress` for pull requests only.
- Jobs on `ubuntu-latest`, each with an explicit `name` equal to its id and a `timeout-minutes`:
  - `backend-static`: `ruff check .`, `ruff format --check .`, `basedpyright`
  - `backend-unit`: `pytest tests/unit -m "not postgres"`
  - `backend-bdd`: `pytest tests/bdd`
  - `tui-static`: `pnpm typecheck`, `pnpm exec biome ci .`
  - `tui-unit`: `pnpm test`
- Backend jobs: `defaults.run.working-directory: backend`, `actions/checkout@v6`, `astral-sh/setup-uv@v10` (`working-directory: backend`, cache enabled), `uv sync --frozen`, commands via `uv run --frozen`.
- TUI jobs: `defaults.run.working-directory: tui`, `actions/checkout@v6`, `pnpm/setup@v2` with `working-directory: tui`, `runtime: node@22`, `cache: true`, `cache-dependency-path: tui/pnpm-lock.yaml`, `require-lockfile: true`. The action runs the install.
- No job-level or workflow-level `env` for application settings. Phase 1 makes that unnecessary.

### Success Criteria:

#### Automated Verification:

- `uvx --from actionlint-py actionlint .github/workflows/pr-gate.yml` reports no errors

#### Manual Verification:

- `git push -u origin deployment-pr-gate`, open a pull request to `main`: checks `backend-static`, `backend-unit`, `backend-bdd`, `tui-static`, `tui-unit` all run and pass

---

## Phase 3: Property Hunt Job

### Overview

Property hunts run on every pull request as a separate job whose failure is visible and never required.

### Changes Required:

#### 1. Advisory property job

**File**: `.github/workflows/pr-gate.yml`

**Intent**: Actively hunt for counterexamples on every pull request (FR-04). Hypothesis draws fresh random examples per run, and a failure shows as a red check without blocking.

**Contract**:
- Job `backend-property` (`name: backend-property`), backend setup identical to the other backend jobs, running `uv run --frozen pytest tests/property` with a `timeout-minutes` bound.
- No `continue-on-error`: a counterexample fails the job red.
- No `derandomize`, no persisted Hypothesis database.
- Never listed in the ruleset's required checks.

### Success Criteria:

#### Automated Verification:

- `uvx --from actionlint-py actionlint .github/workflows/pr-gate.yml` reports no errors
- `cd backend && uv run pytest tests/property` passes

#### Manual Verification:

- From a throwaway branch off `deployment-pr-gate`, add a property asserting something false, push, and open a draft pull request: `backend-property` is red with the falsifying example in its log while the five blocking checks are green (keep it open for Phase 4)

---

## Phase 4: Protect Main

### Overview

`main` accepts changes only through a pull request whose five blocking checks passed, with no bypass. Agent guides say so.

### Changes Required:

#### 1. Ruleset source of truth

**File**: `.github/rulesets/main.json`

**Intent**: Keep the branch protection reviewable and reproducible in the repository; GitHub holds the live copy after a one-time import.

**Contract**: The repository ruleset body (`POST /repos/{owner}/{repo}/rulesets` shape):
- `name: "main"`, `target: "branch"`, `enforcement: "active"`, `bypass_actors: []`
- `conditions.ref_name.include: ["~DEFAULT_BRANCH"]`, `exclude: []`
- `rules`:
  - `pull_request` with `required_approving_review_count: 0` and every other review requirement `false`
  - `required_status_checks` with `strict_required_status_checks_policy: true`, `do_not_enforce_on_create: false`, and the five contexts `backend-static`, `backend-unit`, `backend-bdd`, `tui-static`, `tui-unit`, each with `integration_id: 15368`
  - `non_fast_forward`
  - `deletion`
- `backend-property` is absent.

#### 2. Agent guides

**File**: `CLAUDE.md`, `AGENTS.md`

**Intent**: Agents stop committing straight to `main` once the gate is live.

**Contract**: One sentence appended to the `## Commits` section of both files (they are identical copies): work happens on a branch and reaches `main` through a pull request gated by `.github/workflows/pr-gate.yml`.

### Success Criteria:

#### Automated Verification:

- `python3 -m json.tool .github/rulesets/main.json` parses
- `uv run --with pyyaml python -c "import json,yaml; w={j['name'] for j in yaml.safe_load(open('.github/workflows/pr-gate.yml'))['jobs'].values()}; r={c['context'] for x in json.load(open('.github/rulesets/main.json'))['rules'] if x['type']=='required_status_checks' for c in x['parameters']['required_status_checks']}; assert r == w - {'backend-property'}, (r, w)"` passes

#### Manual Verification:

- GitHub → Settings → Rules → Rulesets → New ruleset → Import a ruleset → `.github/rulesets/main.json`; the ruleset shows Active with the five checks sourced from GitHub Actions
- `git switch main && git commit --allow-empty -m "chore: gate probe" && git push origin main` is rejected with a rule violation, then `git reset --hard origin/main`
- The Phase 3 draft pull request (only `backend-property` red) shows merging allowed once marked ready; close it without merging and delete its branch
- The `deployment-pr-gate` pull request merges only after all five checks are green, and the resulting `main` commit shows a `pr-gate` push run

---

## Testing Strategy

### Unit Tests:

No new tests. Phase 1 changes test bootstrap only, verified by running the existing unit and BDD suites from a clean worktree.

### Integration Tests:

None in this change. The `[postgres]` cases stay deselected from the gate, and Phase 1 verifies they still pass locally with a derived `DATABASE_URL`.

### Manual Testing Steps:

1. Open the change's own pull request and watch the five blocking checks plus `backend-property`.
2. Prove a red `backend-property` does not block a merge.
3. Import the ruleset and prove a direct push to `main` is rejected.
4. Merge the change's pull request through the gate.

## Performance Considerations

BDD is the slowest check at ~65s locally. Jobs run in parallel, so wall time per pull request is bounded by BDD plus setup; uv and pnpm caches keep dependency installs short. The strict up-to-date policy costs one rebase when `main` moved, which is cheap for a single author.

## Migration Notes

After Phase 4's import, every commit, including agent-driven `/implement` phases, needs a branch and a pull request. A hotfix goes through a pull request too; there is no bypass actor. If the live ruleset is edited in the GitHub UI, re-export it into `.github/rulesets/main.json` in a pull request.

## References

- Effort frame: `context/efforts/deployment/frame.md` (FR-03, FR-04; out-of-scope path filtering)
- Frame log: `context/efforts/deployment/frame-log.md` (`merge-gate-reality`, `bdd-integration-manual`, `path-filter-vs-required`)
- Roadmap slice: `context/efforts/deployment/roadmap.md` (S-01)
- Effort research: `context/efforts/deployment/research.md` (GitHub Container Registry and CI)
- `context/foundation/testing-conventions.md` (unit and BDD blocking, property advisory)
- `context/foundation/rules/contract-testing.md` (in-memory contracts every CI run, real adapters on a separate cadence)
- GitHub REST, repository rulesets: https://docs.github.com/en/rest/repos/rules
- Troubleshooting required status checks: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks
- `astral-sh/setup-uv`: https://github.com/astral-sh/setup-uv
- `pnpm/setup` and pnpm CI guide: https://github.com/pnpm/setup, https://pnpm.io/continuous-integration
