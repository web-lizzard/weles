---
change_id: remember-flow-card-rejection
current_phase: 10
next_step:
next_command: /archive remember-flow-card-rejection
updated: 2026-09-11
---

### Phase 1: Rejection outcome stubs

#### Automated

- [x] 1.1 Add Rejected, the ReviewOutcome alias and FINISHING_OUTCOMES in domain/remember/value_objects.py — c63f414
- [x] 1.2 Rename ReviewEvent.grade to outcome and widen it to ReviewOutcome — c63f414
- [x] 1.3 Add Sitting.guard_outcome and route GradeCardCommand's guard through it — c63f414
- [x] 1.4 Filter non-Grade outcomes out of SchedulingReplay.replay — c63f414
- [x] 1.5 Add domain/remember/outbox.py with CARD_REJECTED and CardRejectedPayload — c63f414
- [x] 1.6 Migrate the 21 ReviewEvent construction sites across src, unit, property and bdd suites — c63f414

#### Manual

- [x] 1.7 Grep domain/remember and application/remember for a surviving .grade and confirm only Scheduler's parameter remains — c63f414

### Phase 2: Rejection settles a card and never reaches the scheduler

#### Tests

- [x] tests generated — b2be10f

#### Automated

- [x] 2.1 Treat a rejection as finishing its card in is_finished and outstanding
- [x] 2.2 Keep a rejected card out of next_card for the rest of the sitting
- [x] 2.3 Return None from SchedulingReplay.replay for a log holding only rejections
- [x] 2.4 Fold only the graded events when a card's log mixes grades and a rejection

#### Triage

- [x] 2.5 SchedulingReplay folds grades belonging to other cards (proof: 882047a) — 5251732
- [x] 2.6 R2-F2 Draw seed must include each event sitting_id in the hash input — fbb3fc2
- [x] 2.7 R2-F3 Draw seed uses exactly eight digest bytes big-endian — fbb3fc2
- [x] 2.8 R2-F4 is_offered is false at exactly opened_at plus resume_horizon — fbb3fc2

### Phase 3: Rejection write-path stubs

#### Automated

- [x] 3.1 Add outbox to remember's UnitOfWork port and to the in-memory unit of work — 3b6177a
- [x] 3.2 Add RejectCardCommand with no Scheduler dependency — 3b6177a
- [x] 3.3 Add POST /review-sittings/{sitting_id}/cards/{card_id}/rejection returning 204 — 3b6177a
- [x] 3.4 Add get_reject_card_command in compose and thread the outbox store into the remember unit of work — 3b6177a
- [x] 3.5 Add the outbox store, appender and reject seam to InMemoryRememberComposition — 3b6177a

#### Manual

- [x] 3.6 Curl the rejection route against a running backend and confirm HTTP 204 with an empty body

### Phase 4: Reject command behaviour

#### Tests

- [x] tests generated — cedfe29

#### Automated

- [x] 4.1 Refuse a rejection under each of the four conditions grading already refuses — 3413efb
- [x] 4.2 Write the review event and the card_rejected envelope inside one unit of work — 3413efb
- [x] 4.3 Leave the scheduling state repository untouched on a rejection — 3413efb

#### Manual

- [x] 4.4 Curl a rejection then read /_outbox and confirm a card_rejected envelope that later reads consumed

#### Triage

- [x] 4.5 R5-F1 card_rejected payload re-stamps rejected_at after model_dump — ca10e39

### Phase 5: Distill discard stubs

#### Automated

- [x] 5.1 Add CardRepository.get and implement it on the in-memory adapter — cc9621e
- [x] 5.2 Add DiscardCardCommand taking card id, reason, detail and discarded_at — cc9621e
- [x] 5.3 Add CardDiscardHandler bound to CARD_REJECTED — cc9621e
- [x] 5.4 Register the discard command and handler in compose and in the worker's handler list — cc9621e
- [x] 5.5 Add a worker seam to InMemoryRememberComposition over its own notes and cards repositories — cc9621e

### Phase 6: Distill discard behaviour

#### Tests

- [x] tests generated — 8564061

#### Automated

- [x] 6.1 Stamp a user_audit Discard carrying the envelope's rejected_at — 064dc4f
- [x] 6.2 No-op on a card that already carries any Discard — 064dc4f
- [x] 6.3 No-op on a card id that names no card — 064dc4f
- [x] 6.4 Log and ack a malformed card_rejected payload without calling the command — 064dc4f

### Phase 7: Acceptance layer for AC-17 and AC-23

#### Automated

- [x] 7.1 Register markers AC-16 through AC-23 in pyproject.toml — efc4339

#### Manual

- [x] 7.2 Author the AC-17 and AC-23 scenarios via /bdd — efc4339
- [x] 7.3 Confirm the new scenarios fail on assertions, not on undefined steps or collection — efc4339
- [x] 7.4 Confirm no existing remember-flow scenario regressed — efc4339

### Phase 8: TUI client, store and binding stubs

#### Automated

- [x] 8.1 Regenerate src/api/generated/schema.d.ts against the running backend — 3c55912
- [x] 8.2 Add rejectCard with a 204 branch ahead of the data guard in src/api/sittings.ts — 3c55912
- [x] 8.3 Add currentCard mapping PresentedCardDTO in src/api/sittings.ts — 3c55912
- [x] 8.4 Add rejectCurrentCard to the sitting store and extend LastAction for retry — 3c55912
- [x] 8.5 Bind the reject key in SittingOverlay behind isBackVisible and add its hint constant — 3c55912
- [x] 8.6 Add rejectCard and currentCard to the six vi.mock factories over src/api/sittings — 3c55912

#### Manual

- [x] 8.7 Run the TUI against a running backend and confirm reveal and the four grades behave as before — 2e8425a

### Phase 9: Reject client and store behaviour

#### Tests

- [x] tests generated — e077407

#### Automated

- [x] 9.1 Resolve rejectCard on a 204 and raise SittingHttpError on a client error — 0cb65da
- [x] 9.2 Re-read current-card after a rejection and apply the presented card to the store — 0cb65da
- [x] 9.3 Push the re-read partition through applyPartition so the poll cannot clobber it — 0cb65da
- [x] 9.4 Route a sitting_expired rejection into recoverFromSittingExpired — 0cb65da

#### Manual

- [x] 9.5 Reject a card in the running TUI and confirm the next card appears with no further keystroke — 2e8425a

#### Triage

- [x] 9.6 R6-F1 Retry re-issues a rejection the backend already recorded (proof: 2e4a84e) — 6a88772

### Phase 10: Overlay gesture behind the reveal gate

#### Tests

- [x] tests generated — d142e47

#### Automated

- [x] 10.1 Fire the reject gesture only while the back is visible — d142e47
- [x] 10.2 Render the reject hint only alongside the back — d142e47

#### Manual

- [x] 10.3 Walk a sitting rejecting one card, open a new sitting, and confirm the card is not offered — 2e8425a
