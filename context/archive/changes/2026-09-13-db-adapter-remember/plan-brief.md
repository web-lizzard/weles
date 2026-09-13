# Remember Persists in Postgres and a Card Rejection Discards the Distill Card Through the Outbox — Plan Brief

> Full plan: `plan.md`

## What & Why
Remember's sittings, review events and scheduling states move onto Postgres, in remember's own
Alembic revision. This is slice S-05 of `db-adapter`, and it delivers FR-04, FR-07 and the second
half of FR-08 in tests. It is the last surface before S-06 switches the daemon over.

## Starting Point
Remember runs on in-memory stores, serialized by a module-global `asyncio.Lock`. Its catalog and
source locator walk distill's repositories. Outbox, capture and distill already have Postgres
adapters, contract suites and relay tests.

## Desired End State
Five remember contract suites pass on `in_memory` and `postgres`. On Postgres:
- remember commands commit their state together with their envelopes;
- two remember units of work run one after the other;
- the three remember queries answer from stored rows;
- a card rejection reaches the worker and discards the distill card.

`compose.py` is untouched.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Remember concurrency | `pg_advisory_xact_lock` with one fixed key, taken at UoW enter | Keeps today's serialization across processes; remember transactions never span a model call. | Plan |
| `GradeCardCommand` `TaskGroup` | Two sequential awaits | `AsyncSession` rejects concurrent operations (probed); the concurrency bought nothing inside one transaction. | Plan |
| Catalog and locator | SQL directly over `distill_cards` / `distill_notes` | One read instead of walking every note, and adapters may read another module's tables. | Plan |
| Reads outside a UoW | `ShortSession…` repositories satisfying the full ports | S-06 becomes a pure composition switch, and the contract suites reuse them. | Frame-log + Plan |
| Sitting `card_ids` | Link table `remember_sitting_cards` | Same shape as the distill and capture tag tables, with uniqueness from the primary key. | Plan |
| Event payload | `kind` + nullable `grade` columns with CHECKs, BIGINT identity PK | The database rejects inconsistent events, and the identity keeps insertion order on ties. | Plan |
| Runtime | No `compose.py` change | The frame puts the switch after all four surfaces (S-06). | Frame |

## Scope

**In scope:**
- remember tables and revision;
- session-bound and short-session repositories;
- SQL catalog and locator;
- SQL UoW with advisory lock;
- `GradeCardCommand` sequential saves;
- contract suites on Postgres;
- query, persistence, lock and relay integration tests.

**Out of scope:**
- `compose.py` and `main.py`;
- per-sitting locks or optimistic versions;
- foreign keys to distill;
- a remember projection of cards;
- BDD on Postgres;
- other command or domain changes.

## Architecture / Approach
Each unit gets a stubs phase and then a behaviour phase, as in S-03 and S-04. Session-bound
repositories flush inside the UoW's session. `SqlAlchemyRememberUnitOfWork` takes the advisory lock
as its first statement and binds the repositories and `SqlAlchemyOutboxAppender` to one session. The
short-session repositories, the catalog and the locator open a session per call.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Schema and repository stubs | Four tables, the revision, types, mapping, six repository stubs | Autogenerate rendering the identity column and interval CHECK |
| 2. Repositories on Postgres | Three contract suites on Postgres, schema constraint tests | Event suite must seed sittings for the FK |
| 3. Catalog and locator stubs | `SqlAlchemyReviewCatalog`, `SqlAlchemyCardSourceLocator` | — |
| 4. Catalog, locator and queries | Two contract suites on Postgres, query integration tests | Orphan-card locator case unreachable on Postgres |
| 5. Unit of work stub | `SqlAlchemyRememberUnitOfWork`, `REMEMBER_LOCK_KEY` | — |
| 6. UoW, lock, atomicity, relay | Advisory-locked UoW, sequential grade saves, persistence and relay tests | Statements after `commit` would run unlocked |

**Prerequisites:** S-04 archived; `TEST_DATABASE_URL` reachable; dev database at `85ec052c2b79`.
**Estimated effort:** six phases, three of them stubs-only.

## Open Risks & Assumptions
- A single user means serializing every remember command costs nothing noticeable.
- The FSRS payload (numbers, nulls, ISO strings) round-trips through JSONB equal.
- `ShortSession…save` commits outside a UoW; only contract seeding uses it.

## Success Criteria (Summary)
- `uv run pytest` green with remember contracts on both ids; basedpyright and ruff clean.
- On Postgres, rejection → worker → distill card discarded and no longer offered.
- The remember revision upgrades, downgrades and shows four tables through the MCP server.
