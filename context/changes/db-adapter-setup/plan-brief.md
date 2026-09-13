# Local Postgres Tooling and MCP Access — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-01 of `db-adapter` gives every later persistence slice a place to stand. The dev
Postgres gets pgvector, the author gets read-only MCP access to local rows (FR-09), and the
backend gets its SQLAlchemy engine and session source plus a self-contained Alembic environment,
proven by a few real-Postgres tests.

## Starting Point

Compose already runs `postgres:16` without the `vector` extension. The SQLAlchemy, asyncpg and
Alembic dependencies are installed but unused, `adapters/db/` is an empty stub, and no test
touches a database.

## Desired End State

The devcontainer runs `pgvector/pgvector:pg16`, and a `postgres` MCP server answers queries
against `weles` in restricted mode. `adapters/out/sqlalchemy/` owns the engine, session factory,
`upgrade_to_head`, `alembic.ini` and `migrations/`, and an empty history upgrades cleanly from
the CLI and from tests. Tests marked `postgres` pass against a fixture-recreated `weles_test`.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Alembic location | `alembic.ini` + `migrations/` inside `adapters/out/sqlalchemy/`, CLI via `-c` | Everything Alembic stays inside the adapter, nothing in `pyproject.toml`. | Plan |
| Adapter home | `adapters/out/sqlalchemy/`; empty `adapters/db/` removed | Matches the layering rule's directory convention. | Plan |
| pgvector | Image only; `CREATE EXTENSION` in the first revision that uses it | Keeps the history empty and leaves the parked pgvector-vs-array call to capture. | Plan |
| Test database | `weles_test`, dropped/created and migrated by a session fixture, URL from `TEST_DATABASE_URL` | No compose-only init scripts, so a GitHub Actions service container works unchanged. | Plan |
| Test selection | `postgres` marker; unreachable Postgres fails loudly | CI selects with one flag, and database tests are never skipped silently. | Plan |
| Test isolation | Real commits, `TRUNCATE` after each test | Later atomicity tests (FR-07) need genuine commit/rollback semantics. | Plan |
| MCP server | `uvx --with 'mcp<2' postgres-mcp==0.3.0 --access-mode=restricted` | Maintained, read-only enforced server-side; the `mcp<2` pin is needed to start. | Frame / Research |
| Postgres as store | SQLAlchemy 2.0 async + asyncpg, confined to adapters | Already decided by the backend-stack ADR and the effort frame. | Frame |

## Scope

**In scope:** compose image and `TEST_DATABASE_URL`; `.mcp.json` Postgres server; adapter
package with engine, session factory, Alembic bridge, `alembic.ini`, dual-path `env.py`, empty
`versions/`; `postgres` marker; Postgres fixtures and four integration tests.

**Out of scope:** GitHub Actions workflow; any revision or `CREATE EXTENSION`; models, tables,
repositories, UoW; wiring into `compose.py`/`main.py` (S-06); `pgvector` Python package;
`testing-conventions.md` (run `/testing-shape` afterwards).

## Architecture / Approach

Infra, then stubs, then behaviour. `env.py` serves two callers. From the CLI it builds its own
async engine from `Settings().database_url`. From `upgrade_to_head` it receives an open sync
connection via `config.attributes`, which avoids `asyncio.run` inside a running loop and skips
`fileConfig`. The session fixture is sync, and the per-test engine fixture is async and
function-scoped, so no asyncpg connection crosses event loops.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Local Postgres with pgvector and MCP access | pgvector image, `TEST_DATABASE_URL`, `postgres` MCP server | Needs a host-side devcontainer rebuild before Phase 3 |
| 2. SQLAlchemy adapter and Alembic environment stubs | Importable symbols, `alembic.ini`, template `env.py`, marker, fixture signatures | basedpyright noise from Alembic's dynamic `context` proxy |
| 3. Postgres engine, session source and empty-history migration | Working engine/session/migration path, 4 green Postgres tests | `env.py` event-loop and logging pitfalls on the programmatic path |

**Prerequisites:** devcontainer rebuilt after Phase 1.
**Estimated effort:** small — three short phases, one of them TDD.

## Open Risks & Assumptions

- `postgres-mcp` 0.3.0 stays on the `mcp` 1.x API; a newer release may lift the pin.
- Reusing the `postgres-data` volume across `postgres:16` → `pgvector/pgvector:pg16` assumes the
  same major (16), which the probe confirmed (16.13).
- Default `uv run pytest` includes Postgres tests; outside the devcontainer, run
  `-m 'not postgres'`.

## Success Criteria (Summary)

- The `postgres` MCP server answers a query on local `weles` and refuses writes.
- `alembic -c src/adapters/out/sqlalchemy/alembic.ini upgrade head` succeeds on an empty history.
- `uv run pytest` is green, Postgres suite included.
