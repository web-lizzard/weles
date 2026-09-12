---
date: 2026-09-12T22:22:00+02:00
topic: "SQLAlchemy 2.0 async API for aggregate persistence and composite field mapping"
topic_slug: sql-alchemy
container_id: db-adapter
tags: [research, sqlalchemy, asyncpg, aggregates, composite, unit-of-work]
last_updated: 2026-09-12
---

# Research: SQLAlchemy 2.0 async API for aggregate persistence and composite field mapping

## Research Question

/research db-adapter sql-alchemy z driver async wyciągnij mi api, które posłuzy nam za zapisanie agregatu. Weź pod uwagę composite fields

## Summary

Weles persists aggregates through domain repository ports (`save` / `add` on full Pydantic roots) and application `UnitOfWork.commit()` — not through SQLAlchemy types in domain or application code. A future `adapters/out/sqlalchemy/` implementation should own one `AsyncSession` per command scope (`postgresql+asyncpg`), map domain → ORM explicitly, and use Session unit-of-work primitives: `add` / `get`+attribute updates / optional `merge`, then `flush` and `commit` inside the UoW boundary. ORM `composite()` maps multi-column value objects to a single attribute; single-field VOs use scalar columns; ordered tuples, opaque dicts, and embedded snapshots typically use JSON/JSONB or child tables; `Instruction` composites are not persisted. Contract tests require bitwise Pydantic equality after round-trip.

## Findings

### Domain persistence contract (what the SQL adapter must satisfy)

Aggregate roots are plain Pydantic models with per-root repository protocols. Cross-aggregate references use typed ids, not held objects (`context/adrs/capture-flow-domain-shape/decision.md:19-20`). `CaptureSessionRepository.save` accepts the full `CaptureSession` (`backend/src/domain/capture/ports.py:49-52`). Application commands own the transaction via `UnitOfWork` and `await uow.commit()` (`backend/src/application/capture/ports.py:14-27`). SQLAlchemy stays inside adapters only; adapters map explicitly between ORM models and domain objects (`context/adrs/backend-stack/decision.md:19-20`).

Repository semantics match in-memory behavior: upsert by root id; a second save overwrites. Contract tests assert `result == entity` after save and get (`backend/tests/unit/capture/contracts/test_capture_session_repository_contract.py:18-27`). Future SQL implementations register alongside in-memory in each contract’s `_IMPLEMENTATIONS` list (same file pattern at `12-14`).

Runtime dependencies already include `sqlalchemy[asyncio]` and `asyncpg` (`backend/pyproject.toml:10-11`). No SQLAlchemy engine, models, or Alembic usage exists under `backend/src/` yet; `backend/src/adapters/db/__init__.py` is an empty stub.

### “Composite fields” in Weles vs SQLAlchemy `composite()`

The codebase does not define a “composite field” domain concept. Relevant patterns:

- **Instruction model** — `Instruction` holds `tuple[InstructionBlock, ...]`; built per LLM turn, not stored (`backend/src/domain/shared/instruction/model.py:69-114`). Out of scope for db-adapter save paths.
- **Wrapper value objects** — e.g. `SessionTopic`, `Coverage` with a single `value` field (`backend/src/domain/capture/value_objects.py`). Map to one SQL column each, not ORM `composite()` unless a VO spans multiple columns.
- **Nested state on roots** — e.g. `CaptureSession.assessments: tuple[Coverage, ...]` (`backend/src/domain/capture/capture_session.py:27-36`). Schema choice: JSON array preserving order or normalized child rows; not dictated by SQLAlchemy Session API.
- **Id references vs embedded snapshots** — capture `Note` stores `topic_id` and `tag_ids`; distill `Note` embeds `TopicSnapshot` / `TagSnapshot` (`backend/src/domain/distill/note.py:19-21`). Adapter maps ids to FK columns and snapshots to JSON or denormalized columns.
- **Opaque blobs** — `OpaqueSchedulerState.payload: dict[str, object]` (`backend/src/domain/remember/value_objects.py:67-76`). JSON serialization is adapter-only.

SQLAlchemy **`composite()`** groups multiple table columns under one Python datatype (typically a dataclass). In 2.0, `Mapped[Point] = composite(mapped_column("x1"), mapped_column("y1"))` persists as separate columns on INSERT/UPDATE. In-place mutation of composite sub-fields is not tracked unless `MutableComposite` is used or the whole composite is reassigned.

### SQLAlchemy 2.0 async Session API (adapter-internal)

**Bootstrap:** `create_async_engine` with an asyncio dialect such as asyncpg; `async_sessionmaker` with `expire_on_commit=False` recommended for async so attributes remain usable after commit without implicit reload (unsupported in async expire path).

**Concurrency:** One `AsyncSession` per asyncio task; do not share across concurrent tasks.

**Save operations:**

| Method | Async | Role in aggregate save |
|--------|-------|-------------------------|
| `session.add()` / `add_all()` | No | New transient root (and children via `relationship` + default `save-update` cascade) → INSERT on flush |
| `await session.get(Model, pk)` | Yes | Load persistent instance; update by assigning attributes or replacing composite/JSON values |
| `await session.merge(instance)` | Yes | Copy detached graph into session when load-by-PK patch is awkward |
| `await session.flush()` | Yes | Emit pending SQL inside open transaction |
| `await session.commit()` | Yes | Flush + commit; typically invoked once per UoW scope |
| `async with session.begin():` | Yes | Transaction boundary with commit on success |

**Practical `repository.save(domain)` flow:** map domain → ORM; `row = await session.get(..., id)`; if missing `session.add(orm)` else `apply_domain_to_orm(row, domain)`; defer `flush`/`commit` to UoW `commit()` so multiple repositories share one session.

**Child tables:** Separate aggregate roots (`Message`, `Note`, `Topic`, `Tag`) use separate tables; one command may touch several repositories before a single commit (e.g. session save plus message/note adds in capture commands).

**Mapping strategies for nested domain fields:**

| Domain shape | Typical ORM mapping |
|--------------|---------------------|
| Single-field VO (`SessionTopic`) | Scalar column |
| Multi-field VO without own table | `composite()` + dataclass |
| Ordered collection on root | JSON/JSONB or child table + FK |
| `Embedding.values` | pgvector column (planned stack per deployment research) |
| Snapshot embeds (distill) | JSON or multiple columns |
| FK lists (`tag_ids`) | PostgreSQL array of UUID or link table |

### Proposed internal adapter surface (not a new domain port)

- **Startup:** `create_async_engine(settings.database_url)` where URL is `postgresql+asyncpg://...`; `async_sessionmaker(engine, expire_on_commit=False)`.
- **SqlAlchemyUnitOfWork:** holds one `AsyncSession`; `__aenter__` opens scope; `commit()` calls `await session.commit()`; `__aexit__` rolls back on failure if commit not called (mirror in-memory UoW semantics).
- **Per-repository classes:** implement existing domain protocols; contain `map_domain_to_orm` / `apply_domain_to_orm` (or dedicated mapper modules); never expose `AsyncSession` outside the adapter package.

Domain-facing API remains `async def save(self, aggregate: T) -> None` (and `add` where ports use that name). SQLAlchemy API is implementation detail behind those methods.

## Code References

- `backend/pyproject.toml:10-11` — `sqlalchemy[asyncio]`, `asyncpg` dependencies
- `backend/src/domain/capture/ports.py:49-52` — `CaptureSessionRepository.save`
- `backend/src/application/capture/ports.py:14-27` — application `UnitOfWork` and `commit`
- `backend/src/domain/capture/capture_session.py:27-36` — root fields including `assessments`
- `backend/src/domain/shared/instruction/model.py:69-114` — composite instruction VO (not persisted)
- `backend/tests/unit/capture/contracts/test_capture_session_repository_contract.py:12-27` — contract equality and `_IMPLEMENTATIONS` hook for SQL
- `context/adrs/backend-stack/decision.md:19-20` — SQLAlchemy confined to adapters, explicit mapping
- `context/adrs/capture-flow-domain-shape/decision.md:19-20` — aggregate roots and id-only cross references
- `backend/src/adapters/db/__init__.py` — empty persistence stub

## External References

- <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.create_async_engine> — async engine; dialect must be asyncio-compatible (e.g. asyncpg)
- <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#synopsis-orm> — `AsyncSession` full ORM; one session per task; `add_all` + `session.begin()` insert pattern
- <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#adding-new-or-existing-items> — `add()` places transient instances for INSERT on next flush; re-associates detached instances
- <https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.merge> — merge copies state from outside object; source stays detached
- <https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.flush> — flush writes pending changes inside transaction
- <https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.commit> — flush + commit; `expire_on_commit` and async reload caveat
- <https://docs.sqlalchemy.org/en/20/orm/cascades.html#save-update> — default `save-update` on `relationship()` propagates `add` to related objects
- <https://docs.sqlalchemy.org/en/20/orm/composites.html> — `composite()` maps column groups to dataclass-like types; 2.0 dataclass support
- <https://docs.sqlalchemy.org/en/20/orm/composites.html#tracking-in-place-mutations-on-composites> — in-place composite mutation requires `MutableComposite` or whole-value replacement
- <https://docs.sqlalchemy.org/en/20/orm/extensions/indexable.html> — JSON `index_property` for tracked nested keys

## Open Questions

- Per-aggregate table design (e.g. `assessments` as JSON vs child table) for `CaptureSession` and remember scheduling opaque state.
- Whether repositories always use get-by-PK patch or `merge` after mapping detached ORM graphs from domain.
- Shared `AsyncSession` wiring in `compose.py` and alignment with existing in-memory UoW rollback semantics on `__aexit__` without `commit`.
