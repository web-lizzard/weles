# Repository Guidelines

Weles is a single-user second brain built around a capture → distill → remember loop (@context/foundation/project-overview.md). The backend is Python 3.12 FastAPI with SQLAlchemy/Postgres (pgvector); the client is a Node 22 Ink TUI.

## Hard Rules

- Backend layering is hexagonal: `domain/` imports nothing from `application/` or `adapters/`; `application/` imports domain only; nothing upstream imports a concrete adapter. See @context/foundation/rules/layering.md.
- Every port gets an in-memory adapter (`adapters/out/in_memory/`) before any SQL/Notion/LLM adapter.
- Repository ports expose a single `save`, never an `add`/`update` pair.
- Also follow @context/foundation/rules/cqrs-lite.md, @context/foundation/rules/exceptions.md, @context/foundation/rules/contract-testing.md and @context/foundation/rules/code-ordering.md.

## Project Structure

- `backend/src/{domain,application,adapters,config}/` — bounded contexts `capture`, `distill`, `remember`, `shared`.
- `backend/tests/{unit,property,integration,bdd,features}/` — layout detailed in @context/foundation/testing-conventions.md.
- `tui/` — Ink CLI; API types generated from the backend OpenAPI schema.
- `context/` — planning workspace: `efforts/`, `changes/<change-id>/` (plan.md, todos.md), `adrs/`, `archive/`, `foundation/`.

## Commands

- `cd backend && uv run pytest` — full backend suite; `-m postgres` tests need `TEST_DATABASE_URL`.
- `cd backend && uv run basedpyright` — type check (also a pre-commit hook).
- `cd tui && pnpm test`, `pnpm typecheck`, `pnpm lint`.
- `cd tui && pnpm generate:api` — regenerate `src/api/generated/schema.d.ts` against a running backend.

## Coding Style

Ruff (line length 88, rules `E,F,I,UP,B`) and basedpyright for `backend/`; Biome for `tui/`. All run via @.pre-commit-config.yaml. Backend imports are `src`-rooted absolute (`from domain.distill...`), never relative.

## Testing

Backend tests are flat module-level `test_*` functions, no classes. New Gherkin tags must be registered under `markers` in @backend/pyproject.toml. Property tests use Hypothesis; mutation testing uses mutmut.

## Commits

Conventional Commits scoped by change or effort id, with phase suffix during implementation: `feat(db-adapter-capture): ... (p2)`, `test(...)`, `docs(...)`, `chore(archive): close <change-id>`.

## Language Policy

Full rule: @context/foundation/rules/language-policy.md.

- Chat replies match the user's language: Polish in → Polish out, English in → English out; mixed input follows the dominant language of the latest message.
- Durable artifacts default to English: files on disk (docs, `context/`, configs, comments), commit messages, PR titles/descriptions, code identifiers, error messages, user-facing strings, and rule/skill/agent instructions.
- Switch artifact language only when the user explicitly asks for that item (e.g. "write the README in Polish"); a Polish chat alone is not an override.
