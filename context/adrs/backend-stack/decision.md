## Context

`context/adrs/repo-shape/` already settled that the backend is Python, built around `pydantic-ai` for LLM integration, running as an authenticated HTTP daemon. This decision builds on that — it does not re-open it, and `pydantic-ai` is not re-decided here.

The duck session `overview-thougts` (see `context/duck-sessions/overview-thougts/`) sketched the surrounding shape: a main loop dispatching capture/remember commands, a Postgres-backed outbox feeding a note-save worker and a flashcard-gen worker, and a controlled tag vocabulary. Several of those threads — single-event-loop worker mechanics, outbox consumption topology — are still `OPEN` in that session and are explicitly **out of scope** here; this decision covers only the framework/library stack, not how workers are scheduled.

Two facts surfaced during this session change the shape of the storage decision specifically:

- The application is meant to follow a hexagonal (ports and adapters) architecture — not yet its own ADR, but settled enough to constrain this one: the domain layer stays plain Python (optionally Pydantic-backed for convenience), deliberately isolated from whatever persistence technology backs it.
- The first adapter built for notes will target **Notion**, not Postgres — a deliberate choice, because the user (the sole client of this tool) already keeps and browses their day-to-day knowledge base in Notion. Postgres remains the store for the outbox, tag vocabulary, flashcards, and sessions from `overview-thougts`.

So this decision has two independent halves: the web/validation framework, and two different persistence-adapter clients (SQL for most state, Notion's API for notes) — both mediated through the same port so the domain never sees either directly.

## Decision

- **FastAPI** is the web framework for the daemon's HTTP API.
- **Pydantic** (v2) is the validation/schema layer at the API boundary. This is not an independent pick — it comes transitively from FastAPI and `pydantic-ai`, both of which build their own type systems on it.
- **`pydantic-ai`** is carried over unchanged from `repo-shape` for LLM integration — not re-decided here.
- **SQLAlchemy** (2.0, async) is the ORM for the Postgres-backed persistence adapters: outbox, tag vocabulary, flashcards, sessions. It is confined entirely inside those adapters — no SQLAlchemy model crosses into the domain layer or is ever returned directly as a FastAPI response model. Adapters map explicitly between SQLAlchemy models and plain domain objects.
- **`notion-client`** is the client library for the notes adapter, which persists notes into the user's own Notion workspace instead of Postgres.

## Consequences

- Two persistence backends exist behind the same "save a note" port from day one — Notion for notes, Postgres for everything else. The hexagonal "storage is swappable" premise is exercised immediately rather than staying theoretical, but there is no unified transaction across them: a Notion write and any related Postgres bookkeeping (e.g. an outbox row) cannot commit atomically. This needs an explicit answer when the note-save worker is designed.
- The first adapter actually built (notes → Notion) never exercises SQLAlchemy or Postgres. That integration path (Alembic migrations, `pgvector` column types) stays untested until the outbox/tags/flashcards work starts.
- Choosing SQLAlchemy over SQLModel (see Alternatives) costs an always-manual mapping step between persistence models and domain objects in every adapter. Accepted deliberately: it makes the domain/persistence boundary a type error to violate rather than a discipline to maintain, because a plain SQLAlchemy declarative model cannot be mistaken for, or returned as, a Pydantic/FastAPI schema.
- `notion-client` returns untyped dicts rather than a schema class, which reinforces the same boundary discipline on the notes side for free — there is nothing dict-shaped that looks tempting to leak upward as a domain or API object.
- `notion-client` is community-maintained, not an official Notion SDK — an accepted maintenance/abandonment risk, taken because it already handles auth, pagination, rate limits, and the versioned API-header contract that a hand-rolled `httpx` client would otherwise have to reimplement.
- Pydantic's presence in the stack is forced by composition (FastAPI + `pydantic-ai`), not independently justified — recorded here so a faster alternative is not mistakenly considered an oversight later.
- Async worker scheduling and outbox-consumption mechanics remain explicitly undecided by this ADR — still open threads from `overview-thougts`, deferred to a future decision.

## Alternatives Considered

1. **Litestar** instead of FastAPI. Newer, arguably cleaner dependency-injection model, ships a built-in SQLAlchemy plugin, and often benchmarks faster. Rejected: for a solo maintainer, FastAPI's ecosystem maturity, documentation depth, and sheer volume of prior art — including what `pydantic-ai` itself is documented against — outweighs Litestar's marginal DX/performance edge.
2. **SQLModel** instead of SQLAlchemy. Fuses the Pydantic schema and the ORM table into a single class, which would cut duplication between API and DB shapes. Initially the recommended pick in this session, then rejected once the hexagonal-architecture direction surfaced: with domain models kept as plain Python/Pydantic and deliberately separate from persistence, the domain/persistence mapping step happens regardless, so SQLModel's duplication-avoidance benefit doesn't apply — while its risk remains, since a SQLModel class inherits from `pydantic.BaseModel` and can be returned directly as a FastAPI response, silently punching through the intended adapter boundary. Plain SQLAlchemy makes that leak impossible rather than merely discouraged.
3. **Raw `asyncpg` with hand-written SQL** instead of an ORM. The most transparent, lowest-dependency option. Rejected: without an ORM, rows still have to be hand-mapped to domain objects — exactly SQLAlchemy's job, done manually, and without Alembic's migration tooling.
4. **Raw HTTPS calls via `httpx`** instead of `notion-client` for the Notion adapter. Removes a community-maintained dependency and its abandonment risk entirely. Rejected: Notion's API carries enough incidental complexity (block pagination, per-endpoint rate limits, a versioned API-header contract) that hand-rolling it would mean reimplementing most of what `notion-client` already provides, for a project where that time is better spent on the product's actual capture/distill/remember loop.
5. **`msgspec`** instead of Pydantic. Faster (de)serialization. Rejected: FastAPI and `pydantic-ai` already commit to Pydantic as their type system; introducing a second one would only add a translation layer at every boundary, with no throughput requirement at this project's scale to justify it.
