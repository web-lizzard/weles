# Distill Persists in Postgres and a Capture Approval Becomes Cards Through the Outbox — Plan Brief

> Full plan: `plan.md`

## What & Why

Distill's notes, cards and read models move onto Postgres behind their existing ports, in distill's
own revision. On Postgres, a capture note approval travels through the outbox into a distill note
and then that note's cards (FR-03, FR-07, FR-08; slice S-04 of `db-adapter`).

## Starting Point

S-02 and S-03 left the outbox and capture on Postgres, with shared column-type, contract-suite and
SQL UoW patterns. Distill runs only on in-memory repositories, in-memory query adapters and a
snapshot UoW.

## Desired End State

Two Postgres repositories, three SQL query adapters and `SqlAlchemyDistillUnitOfWork` pass the same
contract suites as the in-memory adapters. On a real Postgres, `SaveNoteCommand` commits its note
together with `note_saved`. One worker pass turns an approved capture note into a ready distill note
with cards. The daemon stays in memory until S-06.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Snapshot storage | `topic_id`/`topic_label` columns; `distill_note_tags(note_id, position, tag_id, label)` | Consistent with capture's ordered child table and readable through MCP | Plan |
| Cross-module keys | No FKs from distill tables to capture tables | Distill never reads capture's stores | Roadmap / Plan |
| Card discard | Three nullable `discard_*` columns with all-or-none and reason CHECKs | The database rejects half-written discards without a join on every read | Plan |
| Card → note | FK `distill_cards.note_id → distill_notes.id`; suites seed the note | No orphan cards, same stance as capture | Plan |
| Concurrency | No version column or locks; `SKIP LOCKED` claiming plus idempotent commands | A redelivery race ends as a failed envelope whose retry is a no-op | Plan |
| Queries | SQL query adapters in S-04, reading rows into DTOs with a short session per call | The user wants distill fully on Postgres; cqrs-lite forbids aggregate reconstruction in queries | Plan / Frame-log |
| Shared enum type | `StrEnumType` moves to `sqlalchemy/shared/types.py` | Distill must not import capture's adapter package | Plan |
| FR-08 proof | Real `OutboxWorker.run_once()` with the real handlers and deterministic structured task | Proves the relay "through the outbox" without composition changes | Frame / Plan |

## Scope

**In scope:**
- distill's Alembic revision (three tables);
- the note and card repositories;
- three SQL query adapters;
- the SQL UoW;
- contract suites on Postgres;
- command atomicity tests;
- the capture-to-cards relay test.

**Out of scope:**
- `compose.py` / `main.py` and HTTP on Postgres (S-06);
- remember tables and the `card_rejected` relay (S-05);
- versions and locks;
- BDD on Postgres.

## Architecture / Approach

Three stubs → behaviour pairs:
1. schema and repositories (1–2);
2. query adapters, with today's in-memory query tests turned into shared contract suites (3–4);
3. the UoW, command atomicity and the relay (5–6).

Repositories take the caller's session, the UoW owns one session per `async with`, and queries own
a short session per call.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Schema and repository stubs | Column types, rows, CHECKs, revision, repository symbols | Moving `StrEnumType` breaks capture imports |
| 2. Repositories on Postgres | Note and card repositories, both contract suites on two ids | Tag order and discard nulls mapping |
| 3. Query adapter stubs | Three SQL query adapter symbols | — |
| 4. Queries on Postgres | Grouped `list_notes`, detail and card reads into DTOs | SQL recency rule diverging from the in-memory rule |
| 5. Unit of work stub | `SqlAlchemyDistillUnitOfWork` symbol | — |
| 6. UoW, atomicity and relay | Real transactions; FR-03, FR-07 and FR-08 proven on Postgres | Worker pass ordering and a connection held across the model run |

**Prerequisites:** S-03 archived; compose Postgres reachable via `TEST_DATABASE_URL`.
**Estimated effort:** 6 phases, lighter than S-03 because no port changes.

## Open Risks & Assumptions

- Concurrent `note_approved` redelivery surfaces as a primary-key failure and a retry, never as
  silent loss.
- `DeterministicStructuredTaskAdapter` keeps proposing its fabricated control card, which the relay
  test relies on for a discarded card.
- Timestamp precision (microseconds) round-trips exactly through TIMESTAMPTZ, as S-03 showed.

## Success Criteria (Summary)

- The note, card and three query contract suites pass with `in_memory` and `postgres` ids.
- Integration tests on Postgres prove atomic `SaveNoteCommand`, durable discards and the
  approval → note → cards relay.
- `uv run pytest`, `basedpyright` and `ruff` are clean, and the revision upgrades and downgrades on
  the dev database.
