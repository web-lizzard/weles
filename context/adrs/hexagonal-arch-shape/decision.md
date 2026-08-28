## Context

`context/adrs/backend-stack/` already flagged that the backend follows a hexagonal (ports and adapters) architecture — "not yet its own ADR, but settled enough to constrain this one" — and committed to a first pass where the domain layer stays plain Python, optionally Pydantic-backed. This decision is that ADR: it turns the sketch into a rule set concrete enough for `/plan` and `/implement` to apply consistently across every future implementation container, without re-litigating the framework/persistence picks already made in `backend-stack`.

The project's overriding constraint is speed to a working prototype (`context/foundation/project-overview.md`'s capture → distill → remember loop), combined with a fact specific to this stack: a meaningful share of adapters will be LLM-backed (`pydantic-ai`), which makes them slow and costly to exercise on every change. That combination is the actual argument for hexagonal isolation here — it is not architectural taste, it is what makes it affordable to build confidence in business logic without paying for live LLM calls on every CI run.

The raw request left two internal tensions unresolved, worth naming because an unresolved tension here would otherwise let implementation containers diverge from each other:

1. Whether the domain layer or the application layer owns the commit boundary (the request said both "domain exposes ports" in general and "application exposes an explicit commit port" specifically).
2. How "commands must ensure they commit" is actually enforced, rather than merely asked for as a discipline.

Both are resolved below.

## Decision

**Layering and dependency direction.** Domain, application, and adapters are three non-overlapping layers. Domain has zero imports from application or adapters. Application imports domain only. Adapters depend on domain and application (to implement ports and to produce/consume DTOs); nothing upstream ever imports a concrete adapter.

**Domain layer.** Exposes domain-facing ports only — repository-style interfaces and any other domain-service ports, expressed in the domain's own vocabulary, with no notion of transactions, HTTP, or storage technology. Domain entities and value objects may be written as Pydantic `BaseModel` instead of `dataclass` (confirming and generalizing the allowance already made in `backend-stack`). Domain code never imports FastAPI, SQLAlchemy, `notion-client`, `pydantic-ai`, or any other adapter-facing package.

**Application layer — CQRS-lite.** Explicit split into `commands/` and `queries/`:

- **Commands** mutate state through domain aggregates and domain ports, and are the exclusive owners of the commit boundary through an application-defined `UnitOfWork` port — not a domain port. Usage is `async with uow: ...; await uow.commit()`; the context manager rolls back by default on exit if `commit()` was never called, and on any propagated exception. Query handlers never receive a `UnitOfWork` and never call `commit()`.
- **Queries** read directly into DTO shape, bypassing domain-aggregate reconstruction, against the same underlying store commands write to. There is no separate read store or projection in this decision — that is what keeps this "-lite" rather than full CQRS; a genuine read/write store split is future work if it's ever needed.

**DTOs as the one exceptional port.** DTOs are application-layer, data-only types (Pydantic `BaseModel`) returned directly by output adapters (HTTP first) with no further mapping step on the way out — query handlers hand back the DTO an adapter serializes as-is. DTOs live in their own module, structurally distinct from domain models even though both may be `BaseModel` subclasses; nothing beyond `BaseModel` is shared between the two, so no type accidentally satisfies both roles.

**Adapters** implement domain ports and application ports (`UnitOfWork`, query ports) and are the only layer that touches DTOs at the wire boundary.

**Dispatch.** Input adapters receive command/query handlers via constructor injection and call them directly — no command/query bus or mediator in this decision.

**InMemoryFirst.** Every port gets an in-memory adapter before any I/O-bound one. Application and domain logic is behaviorally proven against the in-memory adapter first; SQL/Notion/LLM adapters are added once that behavior is established.

**Contract testing.** Each port has one behavioral contract-test suite, parametrized over its adapter implementations. The in-memory implementation runs that suite on every CI invocation. Real, especially LLM-backed, adapters run the same suite on a separate, non-blocking cadence (on-demand or scheduled) rather than gating ordinary CI — gating CI on live LLM calls is neither affordable nor reliable at this project's scale. The contract must exist and be runnable against any adapter; only its CI cadence differs by adapter cost.

**Exception mapping.** Domain and application raise their own exception types. Only the input adapter (HTTP) translates them into transport-specific responses. Domain and application code never import `FastAPI`/`HTTPException` or any transport-specific error type.

**Directory convention** (non-binding sketch, to keep implementation containers consistent):

```
domain/<context>/{model.py, ports.py, exceptions.py}
application/<context>/{commands/, queries/, dto.py, ports.py}
adapters/in/http/...
adapters/out/{in_memory/, sqlalchemy/, notion/, llm/}
```

## Consequences

- Domain exposes fewer ports than a "pure" reading of the original request implied — it never sees `UnitOfWork` or query ports, both of which live in application instead. Accepted deliberately: it keeps the domain transaction-agnostic, at the cost of "domain exposes ports" no longer being a universal rule — it now has one named exception (application-owned orchestration ports) alongside the DTO exception.
- Default-rollback-on-exit means a forgotten `commit()` fails safe (nothing is persisted) but silently — no error surfaces at the point of the mistake. Accepted for now; a bus-level assertion that a command handler always ends in an explicit commit-or-rollback decision is a plausible later hardening, not decided here.
- No bus/mediator means any future cross-cutting concern that spans commands (e.g., publishing to the outbox after a successful commit, still an open thread from the `overview-thougts` duck session per `backend-stack`) will need either per-handler duplication or introducing a bus later. Deferred, not solved here — direct injection doesn't foreclose adding one, since adapters only ever see handlers through an injected reference.
- Splitting contract-test cadence by adapter cost means the expensive adapters' behavioral correctness is only checked on-demand, not on every change — a real window for adapter drift to go unnoticed between deliberate runs. Mitigated only by treating those runs as a required discipline (e.g., before merging a change to that adapter), not by CI enforcement.
- Same-store queries buy handler-level separation and skip the cost of domain-aggregate reconstruction for reads, not read/write scaling independence. If that's ever needed, it is a new decision, not an extension of this one.
- Domain models and DTOs both being `BaseModel` subclasses is a standing risk of accidental boundary blur (an application handler returning a domain object where a DTO is expected, or vice versa). Mitigated only by module separation and review discipline — the type system does not prevent it, since both are structurally `BaseModel`.

## Alternatives Considered

1. **Domain owns the `UnitOfWork`/commit port**, per the literal "domain exposes ports" framing. Rejected: it would force the domain to model transactions, which is an infrastructure concern; a hexagonal core stays transaction-agnostic by construction, not by convention.
2. **Automatic commit after a successful handler** (a bus or decorator commits unless the handler raised). Rejected in favor of an explicit `await uow.commit()` inside a rollback-by-default context manager: it preserves a command's ability to be a deliberate no-op without special-casing, matches the original intent that commands themselves are responsible for committing, and fails safe rather than failing invisibly in the opposite direction (an unintended commit).
3. **Purely manual `.commit()` with no context manager** — the closest literal reading of the request. Rejected: nothing guarantees a rollback on exception or on an accidentally-skipped commit; the context-manager form keeps the same explicit commit call while adding a safe default.
4. **Command/Query Bus (mediator) from the start.** Rejected for now: it adds registration machinery and indirection before there is a concrete cross-cutting need to justify it. Direct handler injection is simpler for a prototype and does not block introducing a bus later.
5. **One unconditional contract-test suite run against every adapter on every CI invocation.** Rejected: several planned adapters are LLM-backed, making an unconditional real-adapter run in CI both expensive and flaky. Splitting cadence — in-memory mandatory, real-adapter on-demand — keeps the fast feedback loop free while still requiring the contract to exist and be exercisable against any adapter.

## Amendment (2026-08-28)

The original "Exception mapping" rule said only that domain and application raise their own exception types and that the input adapter translates them. This amendment specifies the hierarchy and the mapping mechanism.

**Decision.** Domain and application exceptions share one root, `CoreException(Exception)` — deliberately not `DomainException`, so an application-layer exception inheriting from it doesn't misread as a domain concept. `CoreException` derives a default machine-readable `code` from its own subclass name via snake_case (e.g. `NoteNotFoundError` → `note_not_found`, stripping a trailing `Error`/`Exception`); a subclass overrides `code` explicitly only when the derived value isn't the one wanted (two classes sharing a code, or decoupling the code from a class rename). The input adapter owns exactly one `code → adapter-specific error/status` mapping table and never imports a concrete domain/application exception class — only `CoreException.code()` values cross that boundary, so the layering rule holds in both directions: adapters don't leak upward, and domain/application exception types don't leak into the adapter's dispatch logic. A test walks `CoreException.__subclasses__()` recursively and asserts every discovered `code` has an entry in the adapter's mapping table and that no two subclasses collide on the same `code` — the exhaustiveness a closed enum would have given for free, recovered here as a test instead of a type-checker guarantee.

**Consequences.** Auto-derived, overridable `code` means zero boilerplate for the common case at the cost of losing static (type-checker) exhaustiveness — traded for the subclass-enumeration test above. It also means renaming an exception class silently changes its wire-visible `code` unless the author pins `code` explicitly on rename; not solved structurally, worth a one-line reminder wherever `CoreException` is documented for implementers.

**Alternatives considered.** An enum-valued `kind` class attribute was the initial recommendation — closed vocabulary, exhaustiveness checkable by a type checker — but rejected in favor of the derived-`code` approach as a validated pattern the author already works well with, at the accepted cost of moving exhaustiveness enforcement from the type checker to a test. Dispatch by `isinstance`/a per-class handler registry was also considered and rejected: it would force the adapter to import every concrete domain/application exception class, which is exactly the coupling `code`-based dispatch avoids.
