---
status: closed
created: 2026-09-13
updated: 2026-09-13
---

## Boundaries

**In scope.**

Durable persistence on PostgreSQL, through SQLAlchemy 2.0 async (`asyncpg`) confined to
adapters, as `context/adrs/backend-stack/decision.md` already decided. Schema evolution is
managed by Alembic.

Four persistence surfaces, each durable on its own and each carrying its own Alembic
revision:

- **Outbox** — the shared envelope store every module appends to and the worker claims from.
- **Capture** — capture sessions, messages, notes, topics, tags.
- **Distill** — notes and cards.
- **Remember** — sittings, review events, scheduling states.

They become durable one at a time, in dependency order: outbox, then capture, then distill,
then remember. The outbox comes first because all three modules write to it; remember comes
last because it reads distill's cards and notes.

The running daemon switches to Postgres only once all four surfaces are delivered. An
intermediate mix of Postgres and in-memory surfaces is never a supported runtime. This is a
local development tool with a single user.

Proof of done is automated:

- the existing port contract suites also run against the Postgres implementations;
- integration tests against a real Postgres exercise the surfaces together, with particular
  weight on how the outbox interplays with the three modules.

How each surface handles concurrent writes, and every other adapter-internal mechanism, is
decided in that surface's own change, not here.

**Out of scope.**

Notion publication. `context/adrs/distill-domain-shape/frame.md` defers it; distill's note
record is complete without it, so nothing in this effort writes to Notion.

Application-side database telemetry, such as SQL spans or query logs. Observability here
means the author inspecting rows through a local MCP server, nothing emitted by the daemon.

This effort has no PRD: requirements are minted here as `FR-nn` rather than citing
acceptance criteria.

## Requirements

- **FR-01** — Outbox envelopes survive a daemon restart with their full state.
- **FR-02** — Capture's state survives a daemon restart.
- **FR-03** — Distill's state survives a daemon restart.
- **FR-04** — Remember's state survives a daemon restart.
- **FR-07** — On Postgres, a command's state change and the outbox envelopes it appends commit
  together or roll back together.
- **FR-08** — On Postgres, the outbox carries work across modules end to end:
  - a capture note approval becomes a distill note, and then that note's cards;
  - a remember card rejection becomes a discarded distill card.
- **FR-09** — From an agent session, the author can query the rows of the local development
  database through a Postgres MCP server.
