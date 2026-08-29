---
description: Hexagonal layering and dependency direction for backend/
paths: ["backend/**"]
globs: backend/**
alwaysApply: false
---

# Layering

Full rationale: `context/adrs/hexagonal-arch-shape/decision.md`.

## Dependency direction

Domain, application, and adapters are three non-overlapping layers:

- **Domain** has zero imports from application or adapters. No FastAPI, SQLAlchemy, `notion-client`, `pydantic-ai`, or any other adapter-facing package.
- **Application** imports domain only.
- **Adapters** depend on domain and application (to implement ports and to produce/consume DTOs). Nothing upstream ever imports a concrete adapter.

## Domain layer

Exposes domain-facing ports only — repository-style interfaces and any other domain-service ports, expressed in the domain's own vocabulary, with no notion of transactions, HTTP, or storage technology. Domain entities and value objects may be `pydantic.BaseModel` instead of `dataclass`.

## InMemoryFirst

Every port gets an in-memory adapter before any I/O-bound one. Application and domain logic is behaviorally proven against the in-memory adapter first; SQL/Notion/LLM adapters are added once that behavior is established.

## Directory convention

Non-binding sketch, kept consistent across implementation containers:

```
domain/<context>/{model.py, ports.py, exceptions.py}
application/<context>/{commands/, queries/, dto.py, ports.py}
adapters/in/http/...
adapters/out/{in_memory/, sqlalchemy/, notion/, llm/}
```
