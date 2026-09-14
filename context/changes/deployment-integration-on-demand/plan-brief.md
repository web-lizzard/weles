# Integration Suite On Demand — Plan Brief

> Full plan: `plan.md`

## What & Why

The Postgres lane is the only thing that exercises the SQL adapters production runs on, and `pr-gate` deliberately leaves it out. This slice makes that suite runnable in CI for any commit a person names (FR-05), and makes each run leave a verdict on the commit it tested, so S-05 can refuse to deploy a commit that never passed it (FR-06).

## Starting Point

`pr-gate.yml` runs five blocking checks plus an advisory property job on every pull request, with no Postgres service and no integration lane. The test bootstrap is already hermetic and derives `DATABASE_URL` from `TEST_DATABASE_URL`, so a CI job needs one environment variable.

## Desired End State

A person dispatches the `integration` workflow with a ref, a `pgvector/pgvector:pg16` service starts, and the two commands `pr-gate` skips run against that exact commit. The tested commit then carries an `integration` commit status — `pending`, then `success` or `failure` — linking to the run. Nothing triggers the workflow automatically.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| What the lane runs | `pytest tests/integration` plus `pytest tests/unit -m postgres` | Exactly the complement of `pr-gate`, so nothing is tested twice and nothing is left untested. | Plan |
| Trigger | `workflow_dispatch` with a required `ref` input | "Any commit" in FR-05 means an arbitrary SHA, not just a branch head. | Plan |
| Postgres in CI | `services:` with `pgvector/pgvector:pg16` | Same image as the devcontainer, so `vector` and the role's `CREATE DATABASE` rights behave identically. | Plan |
| Record for S-05 | Commit status `integration` on the resolved SHA | A dispatch run is filed under the workflow branch's head, not the tested ref, so a run lookup would gate on the wrong commit. | Plan |
| Required check? | No — absent from the ruleset | An on-demand context would leave every pull request waiting for a status that never arrives. | Frame log (`path-filter-vs-required`) |

## Scope

**In scope:** one `integration.yml` workflow with a dispatch trigger, a Postgres service, the two suites, a resolved-SHA commit status, and one documentation line in the agent guides.

**Out of scope:** the deploy gate that reads the status (S-05), any automatic trigger, adding the context to the ruleset, Neon branches in CI, and S-04's in-flight schema-upgrade tests.

## Architecture / Approach

A single job on `ubuntu-latest` checks out `inputs.ref`, runs a `pgvector` service container alongside itself, sets only `TEST_DATABASE_URL`, and lets the existing bootstrap and session fixtures build and migrate the test database. Around the suite sits a pair of `gh api` calls publishing a commit status on the SHA resolved from the checkout — the one durable artifact this slice hands downstream.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. On-demand integration workflow | Dispatchable run against a chosen ref with a working Postgres service | First time the Postgres lane runs outside the devcontainer; role rights or healthcheck timing could differ |
| 2. Commit status on the tested SHA | `pending` → `success`/`failure` on the resolved commit | A missing `if: always()` leaves a failed run's commit stuck at `pending`, which reads as "never run" |
| 3. Record the lane | One line in `AGENTS.md` and `CLAUDE.md` | None — documentation only |

**Prerequisites:** S-01 `done` (it is — the hermetic bootstrap and the branch workflow are on `main`). A branch and pull request, since `main` is now gated.

**Estimated effort:** one short session; the manual verification needs pushed commits, so it cannot be done entirely offline.

## Open Risks & Assumptions

- Assumes the official image's `POSTGRES_USER` role is a superuser, which is what lets migrations run `CREATE EXTENSION vector` and the fixtures rebuild databases. Phase 1's manual run is the proof.
- The `integration` status context name is an unversioned contract with S-05; renaming it later breaks the deploy gate unless both change together.
- Three local failures in `tests/integration/postgres/test_schema_upgrade.py` are S-04's untracked red tests, not a defect here — they exist on no committed ref and CI will not collect them.
- Nothing prevents a person from deploying without dispatching this lane until S-05 exists. That gap is intentional and closes in the next slice.

## Success Criteria (Summary)

- A dispatch against an arbitrary `main` SHA runs the integration and `-m postgres` suites green against a `vector`-capable Postgres.
- The tested commit, and only it, carries an `integration` status reflecting the run's outcome, including when the suite fails.
- No event other than a manual dispatch starts the workflow, and no pull request waits on it.
