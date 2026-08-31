# Impl review r3

reviewed at d295ddb

- **change-id**: capture-flow-socratic-conversation
- **scope**: phase 1-9 (backend vertical slice — domain, application, HTTP adapter, BDD acceptance — per explicit request; phases 10-13 (TUI) excluded)
- **date**: 2026-08-31

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | WARNING |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | WARNING |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: NEEDS ATTENTION** (more than two WARNING dimensions)

## Success Criteria run

- `cd backend && uv run basedpyright src/domain/capture src/application/capture src/adapters/out/in_memory/capture src/adapters/http/capture.py src/adapters/compose.py` — `0 errors, 0 warnings, 0 notes`
- `cd backend && uv run pytest tests/unit/capture tests/unit/test_http_error_mapping.py tests/integration/test_capture_http.py -q` — `36 passed`
- `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-01 or AC-02 or AC-03 or AC-04)" -v` — `4 passed`

## Findings

### R3-F1 — WARNING

- **Dimension**: Plan Adherence (DRIFT)
- **Location**: `backend/src/application/capture/commands/send_message.py:84`
- **Evidence:** citation — `context/changes/capture-flow-socratic-conversation/plan.md:405` requires: "`yield ReplyDoneEvent(message_id=agent_message.id.value, content=reply_content.value, topic=session.topic.value)` — outside the `async with` block, after commit." The actual `yield ReplyDoneEvent(...)` at `send_message.py:84-88` sits at the same indentation as the rest of the `async with self._uow as uow:` body opened at line 60 — still inside it, not after it exits. No behavioral difference currently follows: `InMemoryUnitOfWork.__aexit__` (`unit_of_work.py:35-38`) is a no-op once `commit()` has run, and `test_generate_reply_rollback_leaves_nothing_persisted_on_early_close` (`tests/unit/capture/test_send_message_command.py:133`) still passes, confirming rollback-on-early-close is unaffected.
- **Fix:** `GenerateReplyCommand.handle()`'s terminal `ReplyDoneEvent` must be yielded after the `async with self._uow` block exits, not from within it — keep the commit boundary and the terminal yield structurally separate so a future `UnitOfWork.__aexit__` that does more than restore-on-rollback (releasing a real transaction/connection, say) can't silently delay or entangle the client's final event with adapter teardown.

### R3-F2 — WARNING

- **Dimension**: Architecture
- **Location**: `backend/src/adapters/out/in_memory/capture/unit_of_work.py:31-38`
- **Evidence:** citation — `InMemoryUnitOfWork.__aenter__`/`__aexit__` read and write `self.capture_sessions._sessions` and `self.messages._store._messages`: private attributes of `InMemoryCaptureSessionRepository` and, two levels deep, of `InMemoryMessageStore` (owned by `InMemoryMessageRepository`), each access suppressed with `# pyright: ignore[reportPrivateUsage]`.
- **Fix:** give `InMemoryCaptureSessionRepository` and `InMemoryMessageStore` their own snapshot/restore methods for `InMemoryUnitOfWork` to call, instead of reaching past their leading-underscore attributes — a unit-of-work coordinates repositories through their own contract, it does not open their internals.

### R3-F3 — WARNING

- **Dimension**: Pattern Consistency
- **Location**: `backend/src/application/capture/value_objects.py:22-30`
- **Evidence:** citation from two sibling string-backed VOs — `Topic` (`backend/src/domain/capture/value_objects.py:30-34`) and `MessageContent` (`backend/src/domain/capture/value_objects.py:49-54`) both canonicalize via a `field_validator("value", mode="before")` that strips the input before validation (landed at `d9d1592`, fixing R2-F1/R2-F2). `ConfidencePoint.note` has no equivalent before-validator; its `model_validator(mode="after")` only checks `note.strip()` truthiness and stores the raw, un-stripped `note`.
- **Fix:** `ConfidencePoint.note` should canonicalize to its stripped form on construction the same way `Topic.value`/`MessageContent.value` do — `plan.md`'s Critical Implementation Details groups all three ("Every string-backed VO...") under the same non-empty-after-strip discipline; a caller constructing `ConfidencePoint(note="x\r")` directly should not be able to store a value the plan's own R2 fix explicitly ruled out for its siblings.

### R3-F4 — OBSERVATION

- **Dimension**: Plan Adherence (DRIFT)
- **Location**: `backend/src/adapters/compose.py:1`
- **Evidence:** citation — `context/changes/capture-flow-socratic-conversation/plan.md:456-460` names `backend/src/adapters/http/capture.py` as holding "Module-level singletons (store, repos, three stand-in adapters, `UnitOfWork`) constructed once" plus the `Depends`-based providers. The actual composition root landed in a new file, `backend/src/adapters/compose.py` (introduced at `e0acf77`), with `capture.py` importing the providers from it instead.
- **Fix:** none required — record as a benign, deliberate separation of the composition root from route definitions. Worth a line in a future ADR/plan if this split is meant to generalize to other adapters.

## Retractions

None.
