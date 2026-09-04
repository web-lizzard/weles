# Implementation Review r1 — distill-flow-note-lands

reviewed at 8b5b340

change-id: distill-flow-note-lands
scope: full
date: 2026-09-04

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

**Overall: APPROVED**

## Findings

None.

## Notes

- Diff scope: `d863eef^..8b5b340` (all 9 phases), matched file-for-file against each phase's Changes Required — no unlisted paths, no missing paths.
- Boundary rule (`context/adrs/distill-domain-shape/decision.md:107`) verified by grep: `domain/distill/` and `application/distill/` name nothing from `domain.capture`/`application.capture`. The single capture import (`NoteApprovedPayload`) lives only in the adapter (`adapters/out/worker/handlers/note_save.py`), as the plan requires.
- `SaveNoteCommand`'s idempotency check, redelivery no-op logging, `UnitOfWork`-factory-per-call discipline, and `SaveNoteHandler`'s validate/log-and-ack malformed path all match their phase Contracts and are exercised by the corresponding test files.
- `InMemoryUnitOfWork` (distill) mirrors capture's `InMemoryUnitOfWork` snapshot/restore/`_committed` shape at the smaller `notes`+`outbox` member set — consistent with the sibling implementation.
- Two disclosed deviations from the plan text, both already recorded on `todos.md` and neither a defect: `EmptyNoteContentError`/`NoteContentTooLongError` renamed to `DistillEmptyNoteContentError`/`DistillNoteContentTooLongError` (avoids a `CoreException.code()` collision with capture's identically-named exceptions); `adapters/http/errors.py`'s `EXCEPTION_STATUS_MAP` gained two entries not named in any phase's Changes Required, required by the repo-wide exhaustiveness test (`tests/unit/test_http_error_mapping.py`) that every `CoreException` subclass be mapped. Both keep `422`, consistent with every other content-validation error in the map.
- `compose.py` wiring confirmed: `LoggingNoteSaveHandler` fully removed (no remaining references anywhere in `src/`/`tests/`), `SaveNoteHandler` registered in its place, one shared `_outbox_store`/`_outbox_appender` pair behind both capture's and distill's units of work.
- Success Criteria commands run at `8b5b340`: `uv run ruff check src` — all checks passed; `uv run basedpyright` — 0 errors/0 warnings/0 notes; `uv run pytest` — 190 passed.

## Retractions

None (first review of this change).
