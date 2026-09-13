## Current State

Session closed 2026-09-13. The body of `frame.md` is frozen and holds every settled boundary
and requirement.

Nothing is open at effort level. The following is parked for the per-surface changes' own
`/frame` or `/plan`. Carry it there; don't re-decide it here:

- Capture concurrency: the user leaned toward optimistic concurrency, with no lock held across
  the model stream (`application/capture/commands/send_message.py:78-139`). Still to settle: how
  a conflict reaches the client, given that only `CoreException` maps to `ReplyErrorEvent`, and
  given that the reply has already streamed by then.
- Remember concurrency: grade/reveal/reject versus today's module-global `asyncio.Lock`. The user
  accepted the concurrent sitting-open race for now.
- Reads outside a UoW: a short session per call (user decision).
- Also parked:
  - worker claiming: a single worker, or `SKIP LOCKED`;
  - test database choice and per-test isolation;
  - embeddings storage: pgvector or a plain array (similarity is computed domain-side);
  - in-memory adapters kept as the contract baseline, and the final settings switch;
  - SQL versions of the query adapters;
  - remember → distill reads in SQL;
  - who runs `alembic upgrade`: this effort or `deployment`.

## Log

### 2026-09-13 — postgres-sqlalchemy: Postgres via SQLAlchemy async in adapters — ACCEPTED

**Why:** Already decided in `context/adrs/backend-stack/decision.md` (Decision: SQLAlchemy 2.0
async for Postgres adapters, confined to adapters); `alembic`, `asyncpg`,
`sqlalchemy[asyncio]` already in `backend/pyproject.toml`. Not re-litigated here.

### 2026-09-13 — notion-out: Notion publication stays out — ACCEPTED

**Why:** `context/adrs/distill-domain-shape/frame.md` § "Notion is deferred, not reversed":
distill's note record is complete without Notion; publication is a later output adapter.

### 2026-09-13 — migration-as-done: "each module ends with a migration" — OPEN

**Why:** A migration is a work item; the frame needs the observable outcome it stands for.

### 2026-09-13 — outbox-ownership: shared outbox table and transactional atomicity — OPEN

**Why:** One outbox store serves all three UoWs (`backend/src/adapters/compose.py`,
`_outbox_store` passed to capture, distill, remember UoWs); per-module slicing has no natural
owner for it.

### 2026-09-13 — cross-module-reads: remember reading distill's data — OPEN

**Why:** `adapters/out/in_memory/remember/review_catalog.py` and `card_source_locator.py`
consume distill `NoteRepository` / `CardRepository`; the SQL shape of that dependency is
undecided.

### 2026-09-13 — app-layer-untouched: does persistence leave domain/application unchanged — OPEN

**Why:** `get_generate_reply_command` reads the session repository outside the UoW, and remember
relies on an in-process `asyncio.Lock`; both are semantics a real database changes.

### 2026-09-13 — local-observability-mcp: local DB observability and an MCP server — OPEN

**Why:** Raised by the user mid-turn ("a no i observability (lokalne), jakiś mcp skonfigurować").
Ambiguous between app-emitted DB telemetry (existing OTel → Langfuse pipeline in
`backend/src/adapters/telemetry`) and developer/agent-side data inspection via a Postgres MCP;
the two have different readers and different done-criteria.

### 2026-09-13 — migration-as-done: outcome is "state survives restart", one revision per surface — ACCEPTED

**Why:** User: "Dane przeżywają restart … FR dla każdego modułu to po prostu persystencja."
The migration stays as the per-surface schema boundary; the outcome is durability.
**Consequence:** FR-01..FR-04, one per surface.
**Supersedes:** 2026-09-13 — migration-as-done — OPEN.

### 2026-09-13 — outbox-ownership: outbox is its own first surface — ACCEPTED

**Why:** User: sequence starts at outbox, then capture, distill, remember. Grounded in the
shared `_outbox_store` (`backend/src/adapters/compose.py`) and the worker consuming envelopes
from all three modules (`adapters/out/worker/handlers/`).
**Consequence:** Atomicity during the transition window is still open — see
`mixed-runtime`.
**Supersedes:** 2026-09-13 — outbox-ownership — OPEN.

### 2026-09-13 — mixed-runtime: envelopes in Postgres while module state is in memory — OPEN

**Why:** In-memory UoW rollback restores `_outbox_store` snapshots
(`adapters/out/in_memory/capture/unit_of_work.py` `__aexit__`) and cannot undo a Postgres
insert; after restart an envelope can outlive the capture note it references.

### 2026-09-13 — lock-in-adapter: serialisation moves into the Postgres adapters — ACCEPTED

**Why:** User: "lock przenosimy do adaptera", on capture as well as remember. Today the lock is
`asyncio.Lock` injected into the remember in-memory UoW (`adapters/compose.py` `_remember_lock`),
process-local by construction; the application port carries no lock
(`application/remember/ports.py:18-28`), so adapter ownership matches the existing shape.
**Consequence:** FR-05.
**Supersedes:** 2026-09-13 — app-layer-untouched — OPEN (the lock half; the read-outside-UoW
half in capture is a composition detail, not an application change).

### 2026-09-13 — lock-granularity: advisory xact lock per session/sitting id — OPEN

**Why:** User proposed `pg_advisory_xact_lock` by session/sitting id. Capture fits. Remember
does not fully: its lock is module-global and taken at UoW enter
(`adapters/out/in_memory/remember/unit_of_work.py:46`), and `OpenSittingCommand` mints a new
sitting after `latest()`, with no id to lock on.

### 2026-09-13 — tx-across-llm: capture transaction spans the model stream — OPEN

**Why:** `application/capture/commands/send_message.py:78-139` streams the reply inside
`async with self._uow`; an advisory xact lock and open transaction would live for the whole
model turn.

### 2026-09-13 — reads-outside-uow: short session per call, no UoW machinery — ACCEPTED

**Why:** User: "poza uow krótka sesja, bez maszynerii unit of work". The sites are read-only
(`application/capture/commands/send_message.py:66-71` via `adapters/http/capture.py:31-36`;
`OpenSittingCommand` catalog read; all query ports wired directly in `adapters/compose.py`),
and the write path reads again inside its own transaction, so no consistency with it is
needed. Adapter-internal; not a body item.

### 2026-09-13 — mixed-runtime: accepted — runtime switches to Postgres only after all four surfaces — ACCEPTED

**Why:** User: "akceptujemy, to dev lokalny, zresztą bazę możemy podpiąć dopiero jak dostarczymy
całość." With no supported mixed runtime, the envelope-outlives-note window never occurs in use.
**Consequence:** Boundary "daemon switches to Postgres only once all four surfaces are
delivered"; each surface is proven by tests before the switch.
**Supersedes:** 2026-09-13 — mixed-runtime — OPEN.

### 2026-09-13 — lock-granularity: concurrent sitting-open race accepted for now — ACCEPTED

**Why:** User: "ok to na razie akceptujemy, aby nie dodawać." Single user; the only unlockable
case is `OpenSittingCommand` minting after `latest()`.
**Consequence:** Out-of-scope boundary. Remember's other commands still open (Current State 1).
**Supersedes:** 2026-09-13 — lock-granularity — OPEN (remember-open half).

### 2026-09-13 — tx-across-llm: optimistic concurrency on capture instead of a held lock — ACCEPTED

**Why:** User: "może na razie optymistyczna konkurencyjność … małe ryzyko, aby dwa procesy
[pisały] to samo capture (nawet nie listujemy tych sesji)." An optimistic check avoids holding
an advisory lock across the model stream (`send_message.py:78-139`) while still preventing a
silent lost update.
**Consequence:** FR-06.
**Supersedes:** 2026-09-13 — tx-across-llm — OPEN.

### 2026-09-13 — lock-in-adapter: FR-05 retired — REJECTED

**Why:** FR-05 promised serialisation of capture and "today's serialisation" of remember. Both
halves were overturned this turn: capture moves to optimistic concurrency (rejects, does not
serialise), and remember's open race is accepted. FR ids are immutable, so FR-05 is removed
rather than reworded and FR-06 carries the capture outcome.
**Supersedes:** 2026-09-13 — lock-in-adapter — ACCEPTED.

### 2026-09-13 — outbox-interplay-tests: integration tests on Postgres, outbox × modules — ACCEPTED

**Why:** User: "najlepiej w ogóle jakieś integracyjne … szczególnie ważne jest dla mnie
otestowanie współgrania outboxa z resztą modeli." Integration suites today run on in-memory
wiring only (`backend/tests/integration/support/in_memory_*.py`, `test_outbox_http.py`);
contract suites expose an `_IMPLEMENTATIONS` hook with only `in_memory`
(`backend/tests/unit/capture/contracts/test_capture_session_repository_contract.py:12-17`).
**Consequence:** Proof-of-done boundary; FR-07 (atomic append) and FR-08 (relay end to end:
`note_approved` → distill note → `note_saved` → cards; `card_rejected` → discard, per
`adapters/out/worker/handlers/`).

### 2026-09-13 — local-observability-mcp: Postgres MCP for local row queries only — ACCEPTED

**Why:** User: "chodzi o mcp do postgresa tylko, abym lokalnie mógł odpytywać o wiersze."
App-side SQL telemetry goes out of scope. `.mcp.json` today configures only Langfuse.
**Consequence:** FR-09 and an out-of-scope boundary on DB telemetry.
**Supersedes:** 2026-09-13 — local-observability-mcp — OPEN.

### 2026-09-13 — effort-altitude: implementation detail deferred to per-surface changes — ACCEPTED

**Why:** User: "nie wiem, czy chcę tak głęboko wchodzić, bo to effort, poszczególne zmiany będą
miały plan, może też framing … to są już szczegóły implementacyjne." An effort frame feeds
`/roadmap` slicing; concurrency mechanisms, error surfacing, and storage types are change-level.
**Consequence:** FR-06 and the sitting-open-race boundary removed from the body; FR-01..04
trimmed to outcome level; mechanisms listed as parked in Current State.

### 2026-09-13 — tx-across-llm: capture concurrency mechanism — PARKED

**Why:** Optimistic concurrency was the user's lean ("może na razie optymistyczna
konkurencyjność"), but the mechanism and conflict surfacing belong to the capture change.
FR-06 retired with it; its id is not reused.
**Supersedes:** 2026-09-13 — tx-across-llm — ACCEPTED.

### 2026-09-13 — lock-granularity: remember concurrency — PARKED

**Why:** Sitting-open race accepted by the user for now; the rest of remember's concurrency is
left to the remember change.
**Supersedes:** 2026-09-13 — lock-granularity — ACCEPTED.

### 2026-09-13 — cross-module-reads: remember reading distill's data in SQL — PARKED

**Why:** Adapter-level choice for the remember change; the dependency order it forces is already
in the body.
