# Capture Persists in Postgres and Commits Atomically with Its Envelopes — Plan Brief

> Full plan: `plan.md`

## What & Why

Capture's sessions, messages, notes, topics and tags move onto Postgres behind their existing
ports. The capture commands' state changes commit or roll back together with the outbox envelopes
they append (FR-02, FR-07; slice S-03 of `db-adapter`). Before any SQL, vocabulary similarity moves
behind the repository ports, so Postgres can answer it with pgvector.

## Starting Point

S-02 left the outbox on Postgres, with a shared `Base`, a first revision, and contract-suite and
fixture patterns. Capture runs only on in-memory adapters, and cosine similarity is computed in the
domain over `candidates()`.

## Desired End State

Six Postgres capture repositories and `SqlAlchemyCaptureUnitOfWork` pass the same contract suites
as the in-memory adapters. On a real Postgres, the start, reply and approve commands leave state
that survives a fresh engine. An approval's `note_approved` envelope commits with the note, and a
stale session save is rejected. The daemon stays in memory until S-06.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| VO ↔ column mapping | `TypeDecorator` per single-column VO; rows typed as domain VOs | `composite()` cannot build or read unchanged Pydantic VOs (probed), and raw columns let the schema drift | Plan |
| Similarity placement | `nearest(embedding)` on the Topic/Tag ports; `MatchCriteria.accepts` keeps the threshold in the domain | Matches the `capture-flow-domain-shape` ADR and lets Postgres compute the cosine | Plan |
| Embedding storage | pgvector `vector` column with no fixed dimension, cosine via `<=>` | Similarity computed where embeddings live, with mixed dimensions allowed | Plan |
| Embedding precision | `Embedding` canonicalizes values to float32 | pgvector is float4, and exact contract equality needs the same values in every store (probed) | Plan |
| Model change safety | `Embedding.model` plus `embedding_model` column; `nearest` compares the same model and dimension only | Vectors from different models are not comparable, even at equal dimension | Plan |
| Capture concurrency | Optimistic `version` on `capture_sessions`, checked in the adapter, raising `CaptureSessionConflictError` | No lock is held across the model stream, and no update is silently lost | Frame (parked) / Plan |
| Referential integrity | Foreign keys throughout; contract suites seed parents | The database rejects orphans, which matters when rows are inspected through MCP | Plan |
| Session ownership | Repositories take the caller's session; the UoW owns one session per `async with` | Same shape as S-02's appender, so envelopes join the capture transaction | Research |
| FR-07 proof | Integration tests on the real commands with the SQL UoW, no HTTP | Proves the real flow without touching composition, which is S-06's | Plan |

## Scope

**In scope:**
- the similarity port change;
- `Embedding.model` and float32 values;
- capture's Alembic revision with the `vector` extension;
- six Postgres repositories and the SQL UoW;
- optimistic session concurrency;
- the contract suites on Postgres;
- command-level integration tests.

**Out of scope:**
- `compose.py` / `main.py` and HTTP on Postgres;
- re-embedding vocabulary after a model change;
- a vector index and the `pgvector` Python package;
- distill and remember tables;
- row or advisory locks.

## Architecture / Approach

InMemoryFirst: the similarity port and `Embedding` are reshaped and proven in memory first
(Phases 1–2). Schema and repositories follow against the unchanged contract suites (3–4), then the
UoW, concurrency and the command proof (5–6). Every TDD'able unit is a stubs phase followed by a
behaviour phase.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Similarity port and embedding model stubs | `Embedding.model`, `nearest`, `accepts` symbols | ~45 test constructions of `Embedding` gain a model |
| 2. Similarity through the port, in memory | float32 embeddings, in-memory `nearest`, resolver rewired | Reshaped tests lose a case the domain metric covered |
| 3. Capture schema and repository stubs | VO column types, rows, revision with `vector`, repository symbols | Autogenerate renders the custom `vector` type poorly |
| 4. Capture repositories on Postgres | Six repositories, contract suites on both ids | Insert order vs foreign keys; score rounding at the threshold |
| 5. Unit of work and conflict stubs | `SqlAlchemyCaptureUnitOfWork`, `CaptureSessionConflictError` → 409 | — |
| 6. UoW, concurrency and atomic commands | Real transactions, version predicate, FR-02/FR-07 proof | Connection held across the model stream |

**Prerequisites:** S-02 archived; compose Postgres (`pgvector/pgvector:pg16`) reachable via `TEST_DATABASE_URL`.
**Estimated effort:** 6 phases, the largest of the effort's slices so far.

## Open Risks & Assumptions

- After an embedding-model switch, old topics and tags stop matching and duplicates are minted until
  a later re-embed change.
- The SQL cosine may differ from the in-memory helper in the last float digits. Contract fixtures
  keep scores away from the threshold.
- The migration role can `CREATE EXTENSION vector` (true on the compose database).

## Success Criteria (Summary)

- Every capture contract suite passes with `in_memory` and `postgres` ids.
- Command-level tests on Postgres prove durable capture state, an envelope committed atomically
  with it, and a rejected stale save.
- `uv run pytest`, `basedpyright` and `ruff` are clean, and the revision upgrades and downgrades
  on the dev database.
