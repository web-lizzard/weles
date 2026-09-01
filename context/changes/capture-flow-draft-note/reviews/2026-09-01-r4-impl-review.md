# Implementation review r4

reviewed at af2c1a1

| Field | Value |
| --- | --- |
| change-id | capture-flow-draft-note |
| scope | phases 1–10 (backend) |
| date | 2026-09-01 |

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | FAIL |

**Overall: REJECTED**

## Findings

### R4-F1 — CRITICAL

- **Dimension**: Success Criteria
- **Location**: `context/changes/capture-flow-draft-note/todos.md:38-43` (Phase 3 `#### Automated`), commit `d431c49`
- **Evidence**: `command-output` — `Topic.mint`, `Tag.mint`, `Note.draft`, `CaptureSession.draft_note()` and the `Label`/`Embedding` validators stayed at their Phase 2 stub state (`raise NotImplementedError` / no validation) all the way through commit `ac63e4b`, tagged `(p9)`. Re-running the plan's own Phase 3/4/6/7/8 Automated Verification command at the historical closing SHAs proves this:
  ```
  $ git worktree add --detach <tmp> d431c49   # phase 4's own closing commit
  $ cd backend && uv run pytest -q
  FAILED tests/unit/capture/test_model.py::test_aggregate_factories_assign_ids_and_draft_shape
  FAILED tests/unit/capture/test_model.py::test_draft_note_assigns_note_id_and_returns_drafted_note
  FAILED tests/unit/capture/test_model.py::test_draft_note_raises_when_session_cannot_accept_note[closed]
  FAILED tests/unit/capture/test_model.py::test_draft_note_raises_when_session_cannot_accept_note[already_drafted]
  FAILED tests/unit/capture/test_value_objects.py::test_label_empty_after_strip_raises_empty_label_error
  FAILED tests/unit/capture/test_value_objects.py::test_embedding_empty_values_raises_empty_embedding_error
  6 failed, 61 passed in 4.40s
  ```
  Re-run unchanged (same 6 failures, `6 failed, 77 passed`) at `b348b1a`, Phase 8's own closing commit — the failing state persisted across every closing SHA in between (`d431c49`, `f0abf27`/`eecf429`, `5db94a2`/`1391687`/`d756eff`, `b348b1a`). Every one of those phases' plan Success Criteria requires `cd backend && uv run pytest` green (plan.md Phase 4/6/7/8 Automated Verification). `git blame` on `todos.md`'s Phase 3 `3.6` row (`- [x] 3.6 \`cd backend && uv run pytest\` green`) resolves to commit `d431c49` itself — the row was flipped to done inside Phase 4's own stub commit, at a point where the suite it claims is green was in fact red. The suite only turned green when Phase 3's actual Contract (the validators and the three factories) was implemented — six phases late, bundled into Phase 9's commit `ac63e4b` alongside that phase's own routing/assembly work — per `git log -- backend/src/domain/capture/topic.py backend/src/domain/capture/note.py backend/src/domain/capture/value_objects.py`, which shows no commit between `2ee7327` (p2 stubs) and `ac63e4b` (p9) touches those files at all.
- **Fix**: A phase's Automated rows are marked `[x]` only once that phase's own Success Criteria commands have actually been run and are green at that phase's own closing commit. A later phase's commit never silently absorbs an earlier phase's undelivered Contract — every closing SHA between phases must be independently green, or the plan's phase boundaries stop being safe points to bisect or roll back to.

### R4-F2 — WARNING

- **Dimension**: Scope Discipline
- **Location**: `backend/src/adapters/http/errors.py:16-21`
- **Evidence**: `citation` — plan.md's Phase 2 "Changes Required" lists exactly `value_objects.py`, `exceptions.py`, `topic.py`, `tag.py`, `note.py`, `capture_session.py`, `ports.py` (plan.md:136-204); `backend/src/adapters/http/errors.py` is not among them. The `EXCEPTION_STATUS_MAP` entries it contracts are Phase 3 §4's own Contract instead: *"`empty_label`, `label_too_long`, `empty_embedding`, `empty_note_content`, `note_content_too_long` → 422; `session_note_already_drafted` → 409"* (plan.md:252). Commit `2ee7327`, tagged `(p2)`, nonetheless adds all six entries to `EXCEPTION_STATUS_MAP` in `errors.py` a full phase early:
  ```
  +    "empty_label": 422,
  +    "label_too_long": 422,
  +    "empty_embedding": 422,
  +    "empty_note_content": 422,
  +    "note_content_too_long": 422,
  +    "session_note_already_drafted": 409,
  ```
  The values match Phase 3's contract exactly — this is not a wrong-value defect, only an out-of-phase file touch.
- **Fix**: A phase's commit touches only the files listed under that phase's own "Changes Required"; a later phase's contracted edit does not land early even when mechanically convenient — phase boundaries stay meaningful for review and bisection only if each phase's diff matches its own file list.

## Retractions

(none)
