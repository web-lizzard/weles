# Deployment PR Gate — Plan Brief

> Full plan: `plan.md`

## What & Why

`main` should accept a change only through a pull request whose unit and BDD suites passed (FR-03), with property hunts reported on the same pull request without blocking (FR-04). Today there is no CI, commits land directly on `main`, and S-05's deploy gate needs checks it can read.

## Starting Point

No `.github/` exists. The backend suites fail to collect in a clean checkout because `adapters/compose.py` builds `Settings()` at import and the test bootstrap sets its defaults too late.

## Desired End State

Every pull request and every `main` push runs five blocking checks: `backend-static`, `backend-unit`, `backend-bdd`, `tui-static`, `tui-unit`. A separate `backend-property` job goes red on a counterexample but never blocks. A committed ruleset, imported once, rejects direct pushes to `main` and merges without green checks, with no bypass.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Blocking suites | Backend + TUI unit and BDD on every PR, no path filters | Skipped required checks block merges, and backend changes leak into TUI types. | Frame |
| Integration lane | Not in the gate; `[postgres]` unit cases deselected | On demand in S-02, matching contract-testing.md's cadence split. | Frame / Plan |
| Hermetic tests | `tests/conftest.py` supplies placeholders at module level | CI and fresh clones need no env, following the existing offline-defaults pattern. | Plan |
| `DATABASE_URL` placeholder | Derived from `TEST_DATABASE_URL` (database `postgres`) when set | A fixed value would break the Postgres helper's maintenance connection in S-02. | Plan |
| Static checks | ruff, basedpyright, tsc, biome also required | Cheap, and they close the `--no-verify` gap. | Plan |
| Property visibility | Separate red job, not required | A counterexample is unmistakable, and merges stay allowed. | Frame / Plan |
| Protection | Committed ruleset JSON, 0 approvals, strict, no bypass | Solo author can merge own PRs; the setting stays reviewable in the repo. | Frame / Plan |
| Main pushes | Workflow also runs on `push` to `main` | S-05 needs results for the merged commit itself. | Plan |
| Toolchain actions | `setup-uv@v10`, `pnpm/setup@v2` with `node@22` | `pnpm/setup` is the maintained action for pnpm 11. | Research |

## Scope

**In scope:** hermetic backend test bootstrap, `.github/workflows/pr-gate.yml` (five blocking jobs plus property), `.github/rulesets/main.json` and its one-time import, and a one-line PR rule in `CLAUDE.md`/`AGENTS.md`.

**Out of scope:** path filters, the integration and Postgres lane (S-02), images and deploys (S-03, S-05), mutation in CI, a lazy `compose.py` refactor, an OpenAPI/TUI type drift check, SHA-pinned actions.

## Architecture / Approach

One workflow, `pr-gate`, runs parallel jobs per surface, each named with its job id so ruleset contexts match exactly. Hermeticity lives in the test bootstrap rather than the workflow, so the workflow has no application env. The change is implemented on branch `deployment-pr-gate`, and its own pull request is the gate's first run. The ruleset is imported before that pull request merges.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Hermetic Backend Test Bootstrap | Unit + BDD green in a fresh clone with no env | Placeholder `DATABASE_URL` misdirecting the Postgres helper |
| 2. Blocking Checks Workflow | Five checks on every PR and main push | pnpm 11 setup or cache misconfiguration on runners |
| 3. Property Hunt Job | Red-but-mergeable `backend-property` | Flaky property turning routine red noise |
| 4. Protect Main | Active ruleset, no bypass; agent guides updated | Context names drifting from job names |

**Prerequisites:** the author's pending `pydantic-ai-slim[openai]` change (`pyproject.toml`, `uv.lock`) is on `main`. The pending `distill_model` default change lands with its test update, or is reverted.

**Estimated effort:** about half a day, most of it Phase 4's manual GitHub checks.

## Open Risks & Assumptions

- The repository stays public; rulesets on a private repository need a paid plan.
- Every future commit, agent phases included, needs a branch and a pull request, including hotfixes.
- A live ruleset edited in the UI can drift from `main.json` until re-exported.

## Success Criteria (Summary)

- A direct `git push origin main` is rejected, and a PR with a red required check cannot merge.
- A PR whose only red check is `backend-property` can merge.
- `uv run pytest tests/unit -m "not postgres"` and `tests/bdd` pass in a fresh clone with no `.env`.
