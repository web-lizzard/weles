# Code Quality Tooling — Plan Brief

> Full plan: `plan.md`

## What & Why

Neither stack in this repo has a working linter/formatter/type-checker today: `ruff` and `mypy` sit unconfigured as backend dev dependencies, and the TUI has no tooling at all. This change configures both stacks' tools, cleans the existing (small) codebase to a passing baseline, and wires everything into `.pre-commit-config.yaml` so violations block a local commit.

## Starting Point

`backend/pyproject.toml` declares `ruff` and `mypy` with zero config tables. `tui/package.json` has no lint/format dependency at all. `.pre-commit-config.yaml` runs only `trailing-whitespace`. No CI exists anywhere in the repo.

## Desired End State

`uv run ruff check .`, `uv run ruff format --check .`, and `uv run basedpyright` all exit 0 in `backend/`; `pnpm exec biome check .` exits 0 in `tui/`; and a deliberately broken commit to either stack is rejected by the local pre-commit hooks.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Backend type checker | `basedpyright`, replacing `mypy` outright | User chose speed/stricter-defaults over keeping the already-declared mypy dependency | Plan (user question) |
| TUI tool | Biome (not ESLint+Prettier) | Single binary, one config, native workspace support, no Ink-specific rule conflicts found | Plan (user question) |
| Cleanup scope | Fix existing violations now, not just wire tooling | Tools should be enforceable from the first post-change commit | Plan (user question) |
| Enforcement | Pre-commit hooks block the commit, not warn-only | Warn-only defeats the point of wiring this up | Plan (user question) |
| CI | Out of scope — pre-commit only | Research found zero CI infra; adding it is a separate scope decision | Plan (user question) |
| Ruff rules | Practical baseline: `E, F, I, UP, B` | Catches real bugs and modernizes syntax without heavy opinionation | Plan (user question) |
| basedpyright wiring | `local` pre-commit hook via `uv run`, not the mirror hook | basedpyright needs the real installed dependency set; a mirror's isolated venv would need every dep duplicated into `additional_dependencies` | Research |
| Biome config location | `tui/biome.json`, not repo root | `tui/` is the actual pnpm workspace root (`pnpm-workspace.yaml` lives there, not at repo root) | Research |

## Scope

**In scope:** ruff config + cleanup (backend), basedpyright config + cleanup (backend, replacing mypy), Biome config + cleanup (TUI), pre-commit wiring for both stacks with blocking enforcement.

**Out of scope:** CI workflow, ESLint/Prettier, switching TUI build/test tooling, stricter-than-baseline rule sets.

## Architecture / Approach

Each stack gets a config-and-cleanup phase per tool, then its own pre-commit-wiring phase — five phases total, backend first then TUI. Every phase is independently verifiable: the tool runs clean, and (for the two wiring phases) a deliberately broken commit is actually rejected.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Backend — Ruff config + cleanup | `ruff check`/`ruff format` clean on `backend/` | Cleanup scope unknown until the tool actually runs |
| 2. Backend — basedpyright config + cleanup | `basedpyright` clean on `backend/`, `mypy` removed | SQLAlchemy `Mapped[T]` / pydantic-ai-slim known false-positive noise |
| 3. Backend — pre-commit wiring | Bad backend commit is blocked | basedpyright needs a `local` hook, not the standard mirror pattern |
| 4. TUI — Biome config + cleanup | `biome check` clean on `tui/` | None significant — small existing codebase |
| 5. TUI — pre-commit wiring | Bad TUI commit is blocked | Hook must be scoped (`files: ^tui/`) so it never touches the backend |

**Prerequisites:** None — no phase depends on anything outside this change.
**Estimated effort:** Small-to-medium; each phase is config plus a bounded cleanup pass over a small existing codebase.

## Open Risks & Assumptions

- basedpyright's known false-positive patterns on SQLAlchemy 2.0 typed mappings and `pydantic-ai-slim` may require a handful of scoped `# basedpyright: ignore[<rule>]` suppressions in Phase 2 — treated as expected, not a blocker.
- The `local` basedpyright pre-commit hook (Phase 3) depends on `backend/.venv` being synced before commit; not an issue today since developers already run `uv sync` locally, but will need a `uv sync` step whenever CI is added later (out of scope here).

## Success Criteria (Summary)

- `backend/`: `ruff check`, `ruff format --check`, and `basedpyright` all exit 0.
- `tui/`: `biome check .` exits 0.
- A deliberately broken commit to either stack is rejected by `git commit` via the wired pre-commit hooks.
