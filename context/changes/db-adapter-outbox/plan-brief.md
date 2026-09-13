# Outbox Envelopes Persist in Postgres — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-02 of `db-adapter` makes the shared outbox the first durable surface, because capture,
distill and remember all append to it. The outbox table arrives in its own Alembic revision.
Postgres adapters behave exactly like the in-memory ones, and FR-01 is proven in tests.

## Starting Point

The outbox runs only on `InMemoryOutboxStore`, behind a five-test contract suite parametrized over
in-memory only. S-01 left the engine, the Alembic bridge, an empty revision history and Postgres
fixtures scoped to `tests/integration/postgres/`.

## Desired End State

`outbox_envelopes` exists through one revision. The Postgres appender, claimer and envelope query
adapter live in `adapters/out/sqlalchemy/shared/outbox/`, and the outbox contract suite passes
with both `in_memory` and `postgres` ids. Integration tests show:

- an append commits or rolls back with its session;
- full envelope state reads back through a fresh engine;
- `OutboxWorker` retries and dead-letters on Postgres.

The daemon is unchanged.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Postgres as store | SQLAlchemy 2.0 async + asyncpg, one Alembic revision per surface | Settled by the backend-stack ADR and the effort frame. | Frame |
| Runtime wiring | `compose.py` stays in memory; no module uses the Postgres outbox yet | The frame allows no mixed runtime; S-03..S-05 wire UoWs, S-06 the daemon. | Frame |
| Concurrent claims | `FOR UPDATE SKIP LOCKED` in one transaction | The existing disjoint-claims contract test holds on Postgres unchanged. | Plan |
| State transitions | Claimer calls domain `claim`; `ack`/`fail` persist the domain's result | No status logic duplicated in SQL. | Plan |
| Appender session | Takes the caller's `AsyncSession`, never commits | S-03's UoW can make envelopes atomic with module state (FR-07). | Plan |
| Claimer / query sessions | `async_sessionmaker`, one short session per call | Matches the effort's reads-outside-UoW decision. | Frame |
| Query adapter | Postgres `OutboxEnvelopeQueryPort` in this slice | Completes the outbox surface before the runtime switch. | Plan |
| Contract suite | Same file, fixture parametrized `in_memory` + `postgres` (marked) | One suite per port; later surfaces plug in the same way. | Plan |
| Fixture home | `integration.support.postgres`, registered in `tests/conftest.py` | Unit-level contract tests need the database fixtures. | Plan |
| Extra proof | Append atomicity, full state via fresh engine, worker retry/dead-letter | Full state and restart are FR-01; atomicity prepares FR-07. | Plan |

## Scope

**In scope:** base and metadata, `OutboxEnvelopeRow` and mapping, first revision, Postgres
appender/claimer/query adapter, shared Postgres fixtures, updated tooling test, contract suite over
both implementations, two integration modules.

**Out of scope:** `compose.py`/`main.py`, any SQLAlchemy UoW, cross-module relay, stale-claim
recovery, pruning consumed rows, `testing-conventions.md`.

## Architecture / Approach

Stubs, then behaviour, twice. The row mirrors `OutboxEnvelope` one field per column, with the type
split into name and version and the payload stored as JSONB. Claiming locks pending rows with
`SKIP LOCKED`, applies the domain transition and writes it back before commit. The query adapter
reads rows straight into `OutboxEnvelopeDTO`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Outbox schema and appender/claimer stubs | Table via revision, symbols, shared fixtures | S-01's empty-history test must change with the first revision |
| 2. Postgres append and claim | Contract suite green on Postgres, atomicity tests | Claim locks released before write-back break disjointness |
| 3. Envelope query stubs | Query adapter symbol | — |
| 4. Full state and worker on Postgres | Query adapter, four integration tests | Timestamp and JSON round-trip equality |

**Prerequisites:** S-01 archived; compose Postgres reachable at `TEST_DATABASE_URL`.
**Estimated effort:** small-to-medium — four phases, two of them TDD.

## Open Risks & Assumptions

- Envelopes left `processing` by a crashed worker stay stuck, as they do in memory today.
- Autogenerate renders the partial index and CHECK faithfully; the revision is reviewed by hand
  regardless.
- `integration.support.postgres` being loaded for every test is harmless: its fixtures run only
  when requested.

## Success Criteria (Summary)

- `uv run pytest tests/unit/shared/test_outbox_contract.py -v` passes for `in_memory` and `postgres`.
- The dev database upgrades to and downgrades from the outbox revision; the MCP server sees the table.
- `uv run pytest` is green with the Postgres suite included.
