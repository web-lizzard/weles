---
date: 2026-08-28T22:14:08+00:00
topic: "Linter/formatter options that fit the backend and TUI stacks"
topic_slug: null
container_id: code-quality
tags: [research, code-quality, backend, tui, ruff, mypy, eslint, biome, pre-commit]
last_updated: 2026-08-28
---

# Research: Linter/formatter options that fit the backend and TUI stacks

## Research Question

potrzebuje podpiąc linter/formatter pod oba stacki znajdź mi pasujące do stacku opcje

(Need to wire up a linter/formatter for both stacks — find options that fit each stack.)

## Summary

Neither stack currently has a wired linter/formatter. `.pre-commit-config.yaml` only runs `trailing-whitespace`; there is no CI.

- **Backend** (`backend/`, Python ≥3.12, `uv`-managed, FastAPI + Pydantic v2 + SQLAlchemy 2.0 async): `ruff` (>=0.8.0) and `mypy` (>=1.13.0) are **already declared as dev dependencies** but have zero config (no `[tool.ruff]`, no `[tool.mypy]`) and run nowhere. The fitting move is to configure and wire the tools already chosen, not add new ones: `ruff` for both lint and format (it replaces Black/flake8/isort/pyupgrade in one tool and is the tool the project's own ecosystem — FastAPI, Pydantic — uses), plus `mypy` with the `pydantic.mypy` plugin for type checking. The SQLAlchemy mypy plugin should explicitly **not** be added — it's deprecated and breaks on mypy ≥1.11. `pyright`/`basedpyright` is a viable faster alternative to mypy but would mean dropping the already-present `mypy` dependency; no evidence in this repo suggests that's wanted.
- **TUI** (`tui/`, TypeScript ^5, React 19 via `ink` ^7, pnpm workspace, ESM + `moduleResolution: Bundler`): nothing is configured or installed. Two realistic options: (a) ESLint flat config + `typescript-eslint` + `eslint-plugin-react-hooks` + Prettier, or (b) Biome (single Rust binary, lint+format+import-sort in one config, official monorepo support). Biome fully supports TS/JSX/TSX and has ported `rules-of-hooks`/`exhaustive-deps` equivalents, with documented behavioral differences from the ESLint originals. No Ink-specific guidance exists for either tool (confirmed absent, not just unfound).
- Both pre-commit paths exist: `astral-sh/ruff-pre-commit` and `pre-commit/mirrors-mypy` for the backend; either `pre-commit/mirrors-eslint` or the official `biomejs/pre-commit` hooks for the TUI — all can sit in the existing `.pre-commit-config.yaml` alongside the current `trailing-whitespace` hook.

## Findings

### Backend — current state

- `backend/pyproject.toml:1-19` declares `ruff>=0.8.0` and `mypy>=1.13.0` under `[dependency-groups].dev`, but the file has no `[tool.ruff]` or `[tool.mypy]` table.
- `.pre-commit-config.yaml:1-5` runs only `trailing-whitespace` from `pre-commit/pre-commit-hooks@v5.0.0` — no ruff, no mypy.
- No CI workflow exists anywhere in the repo (only `.devcontainer` and `.ordo` YAML found).
- Stack: FastAPI, `pydantic-settings`, SQLAlchemy 2.0 async (`asyncpg`), `alembic`, `notion-client`, `pydantic-ai-slim`.

### Backend — fitting options

- **Ruff for lint + format**, replacing the need for a separate Black/flake8/isort/pyupgrade: "The Ruff formatter is an extremely fast Python code formatter designed as a drop-in replacement for Black" (docs.astral.sh/ruff/formatter/). Config shape: top-level `[tool.ruff]` for `line-length` (88 default, matches Black) and `target-version`; `[tool.ruff.lint]` for `select`/`ignore` (e.g. `E`, `F`, `I`, `UP`, `B`); `[tool.ruff.format]` for formatter options — per docs.astral.sh/ruff/configuration/. The `I` rule set subsumes isort entirely, configurable under `[tool.ruff.lint.isort]` (docs.astral.sh/ruff/settings/#lint_isort), so no separate isort dependency is needed.
- **Wiring**: `astral-sh/ruff-pre-commit` provides hook ids `ruff-check` and `ruff-format`. The repo's own README states the lint hook should run *before* the format hook when using `--fix`, "because ruff format should never introduce new lint errors" (github.com/astral-sh/ruff-pre-commit).
- **mypy stays the fitting type checker** for this exact stack given it's already a listed dependency, but needs config: `plugins = ["pydantic.mypy"]` under `[tool.mypy]` for full Pydantic v2 model introspection (pydantic.dev/docs/validation/latest/integrations/dev-tools/mypy/). Do **not** add the SQLAlchemy mypy plugin — SQLAlchemy's own docs mark it "DEPRECATED... will be removed in the SQLAlchemy 2.1 release" and note it "is supported only up until mypy 1.10.1... will have issues running with 1.11.0 or greater" (docs.sqlalchemy.org/en/20/orm/extensions/mypy.html); SQLAlchemy 2.0's PEP 484-native mapping syntax makes the plugin unnecessary.
- **Wiring mypy**: `pre-commit/mirrors-mypy`, hook id `mypy`. Important caveat from the hook's own README: pre-commit runs mypy "from an isolated virtualenv (without your dependencies)," so `additional_dependencies` in the hook config needs to list the project's typed deps (`pydantic`, `sqlalchemy`, `fastapi`, `asyncpg`, etc.) or mypy will treat those imports as untyped (github.com/pre-commit/mirrors-mypy).
- **Alternative considered and not recommended as a default**: `pyright`/`basedpyright` is reportedly 2–5x faster and caught more errors than mypy in one independent 2026 comparison on a ~40K-line FastAPI project, but that same source calls mypy's plugin ecosystem (Pydantic, SQLAlchemy stubs) "the strongest argument for staying on mypy" (danilchenko.dev/posts/ty-vs-mypy-vs-pyright/ — single blog source, not authoritative). Since mypy is already the chosen dependency and Pydantic v2 has an official mypy plugin, switching checkers is a bigger decision than this research scopes to.

### TUI — current state

- `tui/package.json:1-27` has no eslint, prettier, or biome in `dependencies`/`devDependencies` — only `typescript`, `tsup`, `tsx`, `vitest`.
- `tui/tsconfig.json:1-10`: `module: ESNext`, `moduleResolution: Bundler`, `jsx: react-jsx`, `strict: true`.
- No `.eslintrc*`, `eslint.config.*`, `.prettierrc*`, or `biome.json` anywhere in the repo.
- Stack: TS ^5, React ^19 rendered through `ink` ^7 (terminal UI, non-DOM JSX), `zustand`, `openapi-fetch`/`openapi-typescript`, tested with `vitest` + `ink-testing-library`, part of a pnpm workspace (`pnpm-workspace.yaml`, `packageManager: pnpm@11.24.0`).

### TUI — fitting options

- **Option A — ESLint flat config + typescript-eslint + Prettier**: `typescript-eslint.io/getting-started/` gives the current flat-config setup (`eslint @eslint/js typescript typescript-eslint`, `tseslint.configs.recommended`). React hooks linting via `eslint-plugin-react-hooks`'s flat config export (`reactHooks.configs.flat.recommended`), with an experimental `recommended-latest` variant for the React compiler rules.
- **Option B — Biome**: single Rust binary covering lint + format + import organization. Biome's own compatibility matrix marks JS/TS/JSX/TSX all fully supported (✅), not beta (biomejs.dev/internals/language-support/). It ports `rules-of-hooks` as `useHookAtTopLevel` and `exhaustive-deps` as `useExhaustiveDependencies`, but documents behavioral differences from the ESLint originals (e.g. treats `useRef` results as stable and won't warn on missing `ref.current` deps; flags some "unnecessary" deps ESLint allows) — biomejs.dev/linter/rules/use-hook-at-top-level/, biomejs.dev/linter/rules/use-exhaustive-dependencies/, github.com/biomejs/biome/issues/2149.
- **No Ink-specific guidance found** in either tool's docs or issue trackers — confirmed absent rather than just unfound. No `moduleResolution: Bundler`-specific caveics were found for either tool either.
- **Monorepo/pnpm workspace fit**: Biome has native monorepo support since v2 — root `biome.json` plus package-level `{"root": false, "extends": "//"}`, resolved by walking up from cwd (biomejs.dev/guides/big-projects/); no pnpm-specific caveat documented. No equivalent official ESLint+pnpm-workspace doc was found — a per-directory flat-config glob setup is the closest available guidance, but this is inferred, not cited.
- **Wiring into the repo's existing pre-commit pipeline**: `pre-commit/mirrors-eslint` (hook id `eslint`, plugins go under `additional_dependencies`, TS files need `files: \.[jt]sx?$`) vs. the official `biomejs/pre-commit` hooks (`biome-check`, `biome-format`, `biome-lint`, `biome-ci`), e.g. `repo: https://github.com/biomejs/pre-commit`, `rev: "v2.0.6"`, `additional_dependencies: ["@biomejs/biome@2.1.1"]` (biomejs.dev/recipes/git-hooks/).
- **Performance/maturity signal**: Biome's own site claims "~35x Faster than Prettier when formatting 171,127 lines of code in 2,104 files" (biomejs.dev) — self-reported, not third-party verified, but directionally consistent with it being a single Rust binary vs. two separate JS-based tools (ESLint + Prettier).

## Code References

- `backend/pyproject.toml:1-19` — dev deps include unconfigured `ruff` and `mypy`, no `[tool.ruff]`/`[tool.mypy]` tables
- `.pre-commit-config.yaml:1-5` — only `trailing-whitespace` hook currently wired
- `tui/package.json:1-27` — no lint/format tooling in deps; scripts limited to build/dev/test/typecheck/generate:api
- `tui/tsconfig.json:1-10` — `moduleResolution: Bundler`, `jsx: react-jsx`, `strict: true`
- `.vscode/extensions.json:1-3` — recommends `ms-python.python`, `eamodio.gitlens`; no linter/formatter extension recommended for either stack

## External References

- <https://docs.astral.sh/ruff/formatter/> — "The Ruff formatter is an extremely fast Python code formatter designed as a drop-in replacement for Black"
- <https://docs.astral.sh/ruff/configuration/> — default config shape (`line-length` 88, `target-version`), unified lint/format config strategy
- <https://docs.astral.sh/ruff/settings/#lint_isort> — Ruff's `I` rule set "encompasses all isort-related checks and configurations"
- <https://github.com/astral-sh/ruff-pre-commit> — official pre-commit hook ids `ruff-check`/`ruff-format`, ordering caveat when using `--fix`
- <https://docs.sqlalchemy.org/en/20/orm/extensions/mypy.html> — SQLAlchemy mypy plugin "DEPRECATED... will be removed in the SQLAlchemy 2.1 release," breaks on mypy ≥1.11
- <https://pydantic.dev/docs/validation/latest/integrations/dev-tools/mypy/> — official `pydantic.mypy` plugin, `[tool.mypy] plugins = ["pydantic.mypy"]`
- <https://github.com/pre-commit/mirrors-mypy> — official mypy pre-commit mirror; `additional_dependencies` needed since the hook runs in an isolated virtualenv
- <https://www.danilchenko.dev/posts/ty-vs-mypy-vs-pyright/> — independent 2026 comparison of mypy/pyright/ty on a FastAPI-sized codebase (blog source, cited with caveat)
- <https://typescript-eslint.io/getting-started/> — current ESLint flat-config setup for TypeScript
- <https://biomejs.dev/internals/language-support/> — Biome's JS/TS/JSX/TSX support matrix, all marked fully supported
- <https://biomejs.dev/linter/rules/use-hook-at-top-level/> and <https://biomejs.dev/linter/rules/use-exhaustive-dependencies/> — Biome's ports of `rules-of-hooks`/`exhaustive-deps`, with documented behavioral differences
- <https://github.com/biomejs/biome/issues/2149> — discussion of Biome vs ESLint `exhaustive-deps` differences
- <https://biomejs.dev/guides/big-projects/> — Biome's native monorepo config resolution (root + `extends: "//"`)
- <https://github.com/pre-commit/mirrors-eslint> — official ESLint pre-commit mirror, `additional_dependencies` for plugins
- <https://biomejs.dev/recipes/git-hooks/> — official `biomejs/pre-commit` hook ids (`biome-check`, `biome-format`, `biome-lint`, `biome-ci`)
- <https://biomejs.dev/> — Biome's self-reported "~35x faster than Prettier" benchmark claim

## Open Questions

- Whether to keep `mypy` (already a dependency) or switch the backend to `pyright`/`basedpyright` — not decided here; current dependency choice favors staying on mypy.
- Whether to pick ESLint+Prettier or Biome for the TUI — both fit the stack; the decision hinges on preferences not yet stated (single-tool simplicity vs. ESLint's larger rule/plugin ecosystem and exact react-hooks rule parity).
- Exact rule `select` lists and formatter options (quote style, indent) for `[tool.ruff.lint]`/`[tool.ruff.format]`, and the equivalent for whichever TUI tool is chosen, are implementation details for `/plan`, not researched here.
