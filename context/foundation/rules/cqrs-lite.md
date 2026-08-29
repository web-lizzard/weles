---
description: CQRS-lite application layer, UnitOfWork commit boundary, and DTOs for backend/
paths: ["backend/**"]
globs: backend/**
alwaysApply: false
---

# CQRS-lite

Full rationale: `context/adrs/hexagonal-arch-shape/decision.md`.

## Commands and queries split

The application layer splits explicitly into `commands/` and `queries/`.

- **Commands** mutate state through domain aggregates and domain ports, and are the exclusive owners of the commit boundary through an application-defined `UnitOfWork` port — not a domain port. Usage:

  ```python
  async with uow:
      ...
      await uow.commit()
  ```

  The context manager rolls back by default on exit if `commit()` was never called, and on any propagated exception.

- Query handlers **never** receive a `UnitOfWork` and never call `commit()`.
- **Queries** read directly into DTO shape, bypassing domain-aggregate reconstruction, against the same underlying store commands write to. There is no separate read store or projection — that's what keeps this "-lite" rather than full CQRS.

## DTOs

DTOs are application-layer, data-only `pydantic.BaseModel` types returned directly by output adapters (HTTP first) with no further mapping step on the way out — query handlers hand back the DTO an adapter serializes as-is. DTOs live in their own module, structurally distinct from domain models even though both may be `BaseModel` subclasses; nothing beyond `BaseModel` is shared between the two.

## Dispatch

Input adapters receive command/query handlers via constructor injection and call them directly — no command/query bus or mediator.
