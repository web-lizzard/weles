# Neon Schema Script — Plan Brief

> Full plan: `plan.md`

## What & Why

The author must be able to bring the hosted instance's Neon database, empty or behind, to the schema a given commit expects by running one supported script (deployment FR-08, slice S-04). Without it, a deployed backend has no schema to serve from.

## Starting Point

The Alembic history and `upgrade_to_head(engine)` exist, and the first revision already creates `vector`. `alembic upgrade head` cannot target Neon as-is. `env.py` reads the local `.env` through `Settings`, and asyncpg rejects Neon's `sslmode` and `channel_binding` URL params.

## Desired End State

From a checkout of the commit, `NEON_DIRECT_URL=… uv run python scripts/migrate_database.py` previews `current → head`, asks for the database name, and upgrades. It exits 0 without prompting when the database is already current. It refuses pooler URLs, unknown revisions, and unmanaged tables without changing anything.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| What "a commit's schema" means | Head of the checked-out commit's Alembic history | The author checks out the commit to deploy, and the script runs from it | Frame / Plan |
| Data transfer | None | Moving local data into Neon was explicitly not chosen | Frame |
| Deploy/schema ordering | Author's responsibility, documented in README | Accepted risk for a single-operator instance, revisit before the next migration | Frame |
| URL source | `NEON_DIRECT_URL` from `os.environ`, not in `Settings` | Keeps the password out of shell history and away from `.env`, which `Settings` forbids unknown keys in | Plan (user) |
| Before migrating | Preview + type the database name, `--yes` to skip | Same guard as `reset_database.py`, and a typo in the URL cannot silently migrate the wrong database | Plan (user) |
| Connection | Direct host only; pooler refused | PgBouncer transaction mode is unsuitable for DDL | Research |
| Neon URL handling | Rewrite to `postgresql+asyncpg`, `sslmode`→`ssl`, drop `channel_binding` | SQLAlchemy forwards query params as asyncpg kwargs, which reject both | Plan |
| `vector` extension | Nothing new; the first revision creates it | Already in `2ce37af2f0f8` | Research / Plan |
| Refusal type | Plain adapter exception, not `CoreException` | Never crosses HTTP, so it needs no code mapping | Plan |

## Scope

**In scope:** the adapter module (URL, state, upgrade), `scripts/migrate_database.py`, the README runbook, unit and `-m postgres` tests.
**Out of scope:** data moves, downgrades, other target revisions, migrate-on-startup, CI/deploy wiring (S-05), and changes to `env.py`.

## Architecture / Approach

`scripts/migrate_database.py` is thin and calls `adapters/out/sqlalchemy/schema_upgrade.py`. The flow:

1. `direct_asyncpg_url` turns the Neon connection string into an asyncpg URL.
2. `read_schema_state` compares the database's revision with the checkout's head.
3. The script previews and confirms.
4. `upgrade_schema` runs the existing `upgrade_to_head`: one transaction, rolled back as a whole on failure.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Schema Upgrade Stubs | Importable `schema_upgrade` surface | None |
| 2. Schema Upgrade Behavior | URL normalization, state refusals, upgrade to head, tested on Postgres | Fresh-database fixture must drop its database even when a test fails |
| 3. Migration Script and Runbook | Author-facing command and README procedure | Neon specifics (SNI, cold start) only surface in the manual run |

**Prerequisites:** a Neon project with an empty branch for manual verification; `TEST_DATABASE_URL` for the `-m postgres` tests.
**Estimated effort:** under a day.

## Open Risks & Assumptions

- Neon's owner role can run `CREATE EXTENSION vector` (research: pgvector on all plans).
- The pooler is detected by the `-pooler` suffix on the host's first label, Neon's current naming.
- A database migrated by hand outside Alembic is refused rather than adopted; stamping it is the author's manual call.
- Neon agent skills (`npx neon@latest skills -s neon -s neon-postgres -y`) may ease the manual branch setup; not required.

## Success Criteria (Summary)

- An empty Neon branch reaches head with `vector` installed from one command, and a rerun is a no-op.
- Pooler URLs, unknown revisions, and unmanaged tables are refused with nothing changed.
