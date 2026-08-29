# Code Quality Tooling Implementation Plan

## Overview

Wire up linting, formatting, and type checking for both stacks in this repo — the Python backend (`backend/`) and the TypeScript/Ink TUI (`tui/`) — and enforce them locally via pre-commit hooks. Neither stack currently has any of this configured: `ruff` and `mypy` sit unconfigured as backend dev dependencies, and the TUI has no tooling installed at all. `.pre-commit-config.yaml` only runs `trailing-whitespace`.

## Current State Analysis

- `backend/pyproject.toml` declares `ruff>=0.8.0` and `mypy>=1.13.0` under `[dependency-groups].dev` but has no `[tool.ruff]` or `[tool.mypy]` table — neither tool is configured or wired anywhere.
- `backend/src/` is a `src`-layout package (`adapters/`, `application/`, `config/`, `domain/`) managed by `uv`, Python `>=3.12`, `[tool.uv] package = false`. Tests live in `backend/tests/`.
- `tui/package.json` has no lint/format tooling in any dependency group. `tui/tsconfig.json` targets `ES2022`/`ESNext`/`Bundler` resolution, `jsx: react-jsx`, `strict: true`.
- `tui/pnpm-workspace.yaml` (not a repo-root file — `tui/` is its own self-contained pnpm workspace root) declares `packages: [.]`.
- `.pre-commit-config.yaml` at the repo root runs only `pre-commit/pre-commit-hooks@v5.0.0`'s `trailing-whitespace`. No CI workflow exists anywhere in the repo.

## Desired End State

Both stacks have a configured, working lint+format(+type-check) toolchain, the existing (small) codebase in each stack passes clean, and `.pre-commit-config.yaml` blocks a local commit that violates any of them. CI is explicitly out of scope for this change.

Verify by: running each tool directly (Automated Verification per phase) and, for the two pre-commit phases, staging a deliberately broken file and confirming `git commit` is rejected (Manual Verification).

### Key Discoveries:

- `backend/pyproject.toml:1-19` — dev deps include unconfigured `ruff` and `mypy`, no `[tool.ruff]`/`[tool.mypy]` tables (research.md).
- `.pre-commit-config.yaml:1-5` — only `trailing-whitespace` hook currently wired.
- `tui/package.json:1-27` — no lint/format tooling in deps.
- `tui/pnpm-workspace.yaml` lives at `tui/`, not repo root — `tui/` is the actual pnpm workspace root, so Biome's config belongs at `tui/biome.json`, not a repo-root file.
- basedpyright type-checks against actually-installed packages, not stubs — a pre-commit **mirror** hook (isolated venv, like `mirrors-mypy`) would need every runtime dependency duplicated into `additional_dependencies`. The established `uv`-project pattern is a `local` hook that shells into the real synced environment instead.
- Biome's domain-based React rule bundle (`useHookAtTopLevel`, `useExhaustiveDependencies`, etc.) activates on detecting `"react"` in dependencies, independent of `react-dom` — it works for Ink's non-DOM JSX. Biome's `a11y` rules pattern-match on lowercase intrinsic tag names (`img`, `a`) and simply never match Ink's PascalCase components (`Box`, `Text`), so no suppression config is needed.

## What We're NOT Doing

- No CI workflow (GitHub Actions or otherwise) — pre-commit-only enforcement for this change.
- No switch of the TUI's build/test tooling (`tsup`, `vitest` stay as-is).
- No `pyright`/stock — `basedpyright` specifically, replacing `mypy` outright (not run alongside it).
- No ESLint/Prettier — Biome only for the TUI.
- No stricter-than-baseline rule sets (e.g. `ANN`, `D`, `S` for ruff; Biome's `all`/nursery rules) — practical baseline only.

## Implementation Approach

Each stack gets its own config-and-cleanup phase per tool, then its own pre-commit-wiring phase, so each phase is independently verifiable (tool runs clean; then the hook actually blocks a bad commit) and a failure in one stack's wiring never blocks the other stack's phases. Backend goes first (ruff, then basedpyright, then pre-commit), then TUI (Biome, then pre-commit) — order is arbitrary between stacks but each stack's internal order (lint/type config → pre-commit) is load-bearing, since the pre-commit phases assume the underlying tool already runs clean.

## Critical Implementation Details

Pre-commit hook ordering for ruff matters: `ruff-check` must run **before** `ruff-format` when `--fix` is used, because `ruff format` should never introduce new lint errors but a fixer running after formatting could reintroduce formatting drift (per `astral-sh/ruff-pre-commit`'s own README).

The basedpyright pre-commit hook is a `local` hook (`language: system`, `entry: uv run --directory backend --no-sync basedpyright`), not a mirror — see Key Discoveries. This means CI (when it's eventually added, out of scope here) will need its own `uv sync` step before invoking pre-commit; not a concern for this change since no CI exists yet.

---

## Phase 1: Backend — Ruff config and cleanup

### Overview

Configure ruff as the backend's lint+format tool and bring the existing (small) codebase to a clean baseline.

### Changes Required:

#### 1. Ruff configuration

**File**: `backend/pyproject.toml`

**Intent**: Turn the already-declared `ruff` dependency into an active, configured tool covering both linting and formatting, replacing the need for a separate Black/isort/pyupgrade/flake8-bugbear.

**Contract**: Adds `[tool.ruff]` (`line-length = 88`, `target-version = "py312"`), `[tool.ruff.lint]` (`select = ["E", "F", "I", "UP", "B"]`), and `[tool.ruff.format]` (defaults) tables.

#### 2. Existing code cleanup

**File**: `backend/src/**`, `backend/tests/**`

**Intent**: Bring the current codebase to a clean baseline against the new rule set so the tool is enforceable from the next commit onward.

**Contract**: `ruff check --fix .` and `ruff format .` applied; any remaining lint findings ruff can't auto-fix are resolved by hand. No behavior change to application logic.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check .` exits 0
- `cd backend && uv run ruff format --check .` exits 0

---

## Phase 2: Backend — Replace mypy with basedpyright, config and cleanup

### Overview

Swap the unconfigured `mypy` dev dependency for `basedpyright`, configure it, and bring the codebase clean.

### Changes Required:

#### 1. Dependency swap

**File**: `backend/pyproject.toml`

**Intent**: Replace `mypy` with `basedpyright` in the dev dependency group — Pydantic v2's `BaseModel` uses PEP 681's `@dataclass_transform`, which pyright-family checkers implement natively, so no plugin equivalent to `pydantic.mypy` is needed.

**Contract**: Removes `"mypy>=1.13.0"`, adds `"basedpyright>=1.39.10"` under `[dependency-groups].dev`.

#### 2. basedpyright configuration

**File**: `backend/pyproject.toml`

**Intent**: Point basedpyright at the `src`-layout package and test tree, at the tool's own `recommended` default strictness (no override) to match the practical-baseline posture chosen for ruff.

**Contract**: Adds `[tool.basedpyright]` with `include = ["src", "tests"]` and `pythonVersion = "3.12"`.

#### 3. Existing code cleanup

**File**: `backend/src/**`, `backend/tests/**`

**Intent**: Resolve what basedpyright flags. SQLAlchemy 2.0's `Mapped[T]`/`mapped_column` and `pydantic-ai-slim`'s generic agent/tool typing are known sources of pyright-family false positives — genuine tool-limitation findings there are suppressed narrowly rather than worked around structurally.

**Contract**: `# basedpyright: ignore[<rule>]` used only for confirmed tool-limitation false positives, each with the specific rule code (never a bare blanket ignore). Real findings are fixed in the code.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` exits 0

---

## Phase 3: Backend — pre-commit wiring

### Overview

Wire ruff and basedpyright into `.pre-commit-config.yaml` so a local commit touching `backend/` is blocked on violations.

### Changes Required:

#### 1. Ruff hooks

**File**: `.pre-commit-config.yaml`

**Intent**: Add the official ruff pre-commit hooks, ordered so the linter's `--fix` pass runs before formatting.

**Contract**: Adds `astral-sh/ruff-pre-commit` with hook ids `ruff-check` (with `--fix`) then `ruff-format`, both scoped to `backend/`.

#### 2. basedpyright local hook

**File**: `.pre-commit-config.yaml`

**Intent**: Type-check against the real installed dependency set rather than an isolated pre-commit venv — see Critical Implementation Details for why this is a `local` hook, not a mirror.

**Contract**:
```yaml
- repo: local
  hooks:
    - id: basedpyright
      name: basedpyright
      entry: uv run --directory backend --no-sync basedpyright
      language: system
      types: [python]
      files: ^backend/
      pass_filenames: false
```

### Success Criteria:

#### Automated Verification:
- `pre-commit run ruff-check --all-files` exits 0
- `pre-commit run ruff-format --all-files` exits 0
- `pre-commit run basedpyright --all-files` exits 0

#### Manual Verification:
- Stage a deliberately broken file under `backend/` (e.g. an unused import or a type mismatch), attempt `git commit`, confirm the commit is rejected, then discard the staged change.

---

## Phase 4: TUI — Biome config and cleanup

### Overview

Install and configure Biome as the TUI's single lint+format+import-organize tool, and bring the existing (small) TUI codebase clean.

### Changes Required:

#### 1. Dependency and scripts

**File**: `tui/package.json`

**Intent**: Add Biome as the TUI's lint/format tool and expose it via package scripts for local use.

**Contract**: Adds `"@biomejs/biome": "2.5.10"` under `devDependencies`; adds `"lint": "biome check ."` and `"lint:fix": "biome check --write ."` under `scripts`.

#### 2. Biome configuration

**File**: `tui/biome.json`

**Intent**: Enable linting (recommended rules plus the React rule domain, which covers Ink's non-DOM JSX without misfiring on DOM-specific a11y rules), formatting, and import organization, scoped to the `tui/` workspace root.

**Contract**:
```json
{
  "$schema": "https://biomejs.dev/schemas/2.5.10/schema.json",
  "root": true,
  "vcs": { "enabled": true, "clientKind": "git", "useIgnoreFile": true },
  "formatter": { "enabled": true, "indentStyle": "space" },
  "linter": { "enabled": true, "rules": { "recommended": true }, "domains": { "react": "recommended" } },
  "assist": { "actions": { "source": { "organizeImports": "on" } } }
}
```

#### 3. Existing code cleanup

**File**: `tui/src/**`, `tui/test/**`

**Intent**: Bring the current TUI codebase to a clean baseline against Biome's recommended + React-domain rules.

**Contract**: `biome check --write .` applied from `tui/`; any remaining findings Biome can't auto-fix are resolved by hand. No behavior change to application logic.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm install` completes (new dependency)
- `cd tui && pnpm exec biome check .` exits 0

---

## Phase 5: TUI — pre-commit wiring

### Overview

Wire Biome into `.pre-commit-config.yaml` so a local commit touching `tui/` is blocked on violations.

### Changes Required:

#### 1. Biome hook

**File**: `.pre-commit-config.yaml`

**Intent**: Add the official Biome pre-commit hook, pinned to the same version installed in `tui/package.json`, scoped so it never touches the Python backend.

**Contract**:
```yaml
- repo: https://github.com/biomejs/pre-commit
  rev: v2.5.11
  hooks:
    - id: biome-check
      additional_dependencies: ["@biomejs/biome@2.5.10"]
      files: ^tui/
      args: ["--write"]
```

### Success Criteria:

#### Automated Verification:
- `pre-commit run biome-check --all-files` exits 0

#### Manual Verification:
- Stage a deliberately broken file under `tui/` (e.g. an unused variable or a hook called conditionally), attempt `git commit`, confirm the commit is rejected, then discard the staged change.

---

## Testing Strategy

### Unit Tests:
None — every phase is tooling configuration and cleanup of existing code, not new behavior (per the TDD-ability rubric: pure scaffolding and wiring/infra are not TDD'able). No phase carries a `#### Tests` row.

### Integration Tests:
N/A — no phase introduces application behavior to integration-test.

### Manual Testing Steps:
Covered per-phase above (Phases 3 and 5): stage a deliberately broken file, confirm the relevant pre-commit hook blocks the commit, then discard the staged change.

## Performance Considerations

None — ruff, basedpyright, and Biome are all chosen partly for their speed (single-binary/Rust or Rust-based tools); no performance risk introduced.

## Migration Notes

`mypy` is removed outright, not deprecated alongside `basedpyright` — no dual-running period. Anyone with editor integrations pointed at mypy for the backend should switch to basedpyright's editor extension after this change lands.

## References

- `context/changes/code-quality/research.md` — original tool-fit research (ruff/mypy/Biome/ESLint options, pre-commit hook survey)
- <https://docs.basedpyright.com/latest/configuration/config-files/>
- <https://github.com/DetachHead/basedpyright-pre-commit-mirror/blob/main/.pre-commit-hooks.yaml> — surveyed and not used; see Critical Implementation Details
- <https://docs.astral.sh/uv/guides/integration/pre-commit/>
- <https://github.com/astral-sh/ruff-pre-commit>
- <https://biomejs.dev/linter/domains/>
- <https://biomejs.dev/guides/big-projects/>
- <https://github.com/biomejs/pre-commit/blob/main/README.md>
