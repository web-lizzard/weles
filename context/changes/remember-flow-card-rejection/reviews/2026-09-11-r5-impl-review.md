# Implementation review r5

- **change-id**: remember-flow-card-rejection
- **scope**: full
- **date**: 2026-09-11
- **reviewed at** 9fd0796

Phases reviewed: 1 through 7 (started). Phases 8, 9 and 10 are unstarted and were
skipped, not reported as missing.

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | FAIL |
| Success Criteria | PASS |

**Overall: NEEDS ATTENTION** — one non-CRITICAL FAIL.

### Notes on the PASS verdicts

- **Plan Adherence** — every Contract in phases 1 through 7 is present in the diff.
  `Rejected`, `ReviewOutcome` and `FINISHING_OUTCOMES` replace `FINISHING_GRADES` whole
  (`grep -rn "FINISHING_GRADES" src tests` returns nothing); `guard_outcome` raises in the
  documented order; `SchedulingReplay.replay` filters to `Grade` and scopes to the target
  card; `RejectCardCommand.__init__` takes no `Scheduler`; `uow.scheduling_states` is never
  touched on the rejection path; `CardRepository.get` joins the port and its contract suite;
  `compose` appends `CardDiscardHandler` to the worker; markers `AC-16` through `AC-23` are
  registered contiguously. Phase 1's Manual grep is clean —
  `grep -rn "\.grade\b\|grade=" src/domain/remember src/application/remember` returns
  nothing, the `Scheduler.review` signature parameter being the only surviving `Grade` use.
  The one deviation found is non-behavioral and is carried under `R5-F1` below, where the
  sibling evidence is stronger.
- **Safety & Quality** — no candidate survived the admissibility gate. The rejection path
  writes the review event and the envelope inside one unit of work and is already pinned
  against a failing append (`tests/unit/remember/test_reject_card_command.py:179`); the
  distill discard is idempotent on redelivery and on an unknown card id, with
  `discarded_at` taken from the envelope rather than a clock.
- **Architecture** — the adapter-only import direction holds.
  `adapters/out/worker/handlers/card_discard.py:7` imports `domain.remember.outbox`, which
  the plan sanctions; `grep -rn "remember" src/application/distill src/domain/distill`
  returns nothing, so `distill` itself never names `remember`.
- **Success Criteria** — every Automated Verification command on phases 1 through 7 was
  run at `9fd0796` and exited 0. See `R5-F0` evidence below.

## Findings

### R5-F1

- **Id**: `R5-F1`
- **Severity**: WARNING
- **Dimension**: Pattern Consistency
- **Location**: `backend/src/domain/remember/outbox.py:17`
- **Evidence:** `citation`

  `backend/src/domain/remember/outbox.py:15-18`:
  ```python
  def to_envelope(self) -> OutboxEnvelope:
      payload = self.model_dump(mode="json")
      payload["rejected_at"] = self.rejected_at.isoformat()
      return OutboxEnvelope.pending(CARD_REJECTED, payload)
  ```

  Sibling 1 — `backend/src/domain/distill/outbox.py:13-14`:
  ```python
  def to_envelope(self) -> OutboxEnvelope:
      return OutboxEnvelope.pending(NOTE_SAVED, self.model_dump(mode="json"))
  ```

  Sibling 2 — `backend/src/domain/capture/outbox.py:42-43`, on a payload that also carries
  a `datetime` (`approved_at: datetime`, line 25) and still does not re-stamp it:
  ```python
  def to_envelope(self) -> OutboxEnvelope:
      return OutboxEnvelope.pending(NOTE_APPROVED, self.model_dump(mode="json"))
  ```

  The two agreeing siblings hand `model_dump(mode="json")` to `OutboxEnvelope.pending`
  untouched; the new payload invents a third shape by overwriting one serialized field
  after the dump. The observable result is a wire format that disagrees with every other
  envelope this system writes:

  ```
  plain dump : {'card_id': '4dcd…', 'rejected_at': '2026-09-11T10:00:00Z'}
  to_envelope: {'card_id': '4dcd…', 'rejected_at': '2026-09-11T10:00:00+00:00'}
  roundtrip plain: 2026-09-11 10:00:00+00:00
  ```

  The third line shows the override is not load-bearing —
  `CardRejectedPayload.model_validate(self.model_dump(mode="json"))` already recovers the
  exact instant, so `CardDiscardHandler` reads the same `rejected_at` either way.

  The same line also contradicts the phase 1 Contract, `plan.md:204`, verbatim:
  "`to_envelope() -> OutboxEnvelope` returning
  `OutboxEnvelope.pending(CARD_REJECTED, self.model_dump(mode="json"))`". Non-behavioral
  drift, so it is reported once, here, rather than twice.

- **Fix:** An outbox payload's `to_envelope` must hand `self.model_dump(mode="json")` to
  `OutboxEnvelope.pending` unmodified; no field may be re-serialized after the dump. If a
  field genuinely needs a non-default wire form, it belongs in a pydantic field serializer
  on the payload, not in a post-dump mutation — and then the plan Contract has to say so.

### R5-F2

- **Id**: `R5-F2`
- **Severity**: OBSERVATION
- **Dimension**: Scope Discipline
- **Location**: `backend/tests/integration/conftest.py:121`
- **Evidence:** `citation`

  `backend/tests/integration/conftest.py:118-121` adds a field to `RememberTestContext`:
  ```python
  client: TestClient
  notes: InMemoryDistillNoteRepository
  cards: InMemoryCardRepository
  outbox_store: InMemoryOutboxStore
  ```

  No phase's Changes Required names `backend/tests/integration/conftest.py`. Phase 3's
  Contract for the test seam names only
  `backend/tests/integration/support/in_memory_remember.py` (`plan.md:344-350`), and the
  Testing Strategy names `backend/tests/integration/test_remember_routes.py`
  (`plan.md:726-727`) but not the fixture module that feeds it.

  Benign: the field exists so
  `test_reject_card_returns_204_and_queues_card_rejected_on_the_remember_outbox` can read
  the envelope the route wrote. It violates nothing in What We're NOT Doing. Recorded, not
  queued.

- **Fix:** The integration fixture may expose composition fields the route tests read; if
  this one stays, phase 3's Changes Required should name
  `backend/tests/integration/conftest.py` alongside the support module rather than leaving
  the path unaccounted for.

### R5-F0 — Success Criteria command output

Not a finding; recorded here because the dimension's evidence kind is `command-output` and
every reviewed phase's Automated Verification was run.

- Phases 1, 3, 5 — `cd backend && uv run pytest` → `455 passed, 1 warning in 22.49s`,
  exit 0. The single warning is the pre-existing
  `PytestAssertRewriteWarning: Module already imported so cannot be rewritten: bdd.steps.capture`.
- Phases 1, 3, 5 — `cd backend && uv run basedpyright src` →
  `0 errors, 0 warnings, 0 notes`, exit 0.
- Phase 2 — `tests/unit/remember/test_sitting.py`,
  `tests/unit/remember/test_scheduling_replay.py`, `tests/property/remember`; phase 4 —
  `tests/unit/remember/test_reject_card_command.py`,
  `tests/integration/test_remember_routes.py`; phase 6 —
  `tests/unit/distill/test_discard_card_command.py`,
  `tests/unit/distill/test_card_discard_handler.py`,
  `tests/unit/distill/contracts/test_card_repository_contract.py`; phase 7 —
  `tests/bdd/test_remember_step_coverage.py`. Run together:
  `75 passed in 2.51s`, exit 0.
- Phase 7 — `cd backend && uv run pytest tests/bdd -m "remember-flow" -v` →
  `28 passed, 25 deselected, 1 warning in 0.26s`, exit 0. No `PytestUnknownMarkWarning`.

## Retractions

(none — no finding this review mapped to `proof-test`, so the proof ritual wrote no tests
and there is no evidence commit. Rows carry no `(proof: …)` marker.)

## Dedup against predecessors

- `r1` (`R1`, phase 2 property) — its finding closed as todos row `2.5`; not re-raised.
- `r2` (`R2-F1` through `R2-F4`, phase 2 mutation) — `R2-F1` was killed in review; `R2-F2`,
  `R2-F3` and `R2-F4` closed as todos rows `2.6`, `2.7`, `2.8`. `_draw_seed` still carries
  the real `sitting_id` (`sitting.py:184`) and the eight big-endian digest bytes
  (`sitting.py:188`); `is_offered` is still strict `<` (`sitting.py:106`). Not re-raised.
- `r3` (phase 4 mutation) — no specimens.
- `r4` (`R4-F1`, phase 6 mutation) — killed in review by
  `test_discard_stamps_a_non_none_detail_onto_the_card`, queued no row. `detail=detail`
  still stands at `discard_card.py:33`. Not re-raised.
- No prior artifact recorded a retraction, so nothing was carried forward.
