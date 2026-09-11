---
change_id: remember-flow-card-rejection
current_phase: 1
next_step: 1.1
next_command: /implement remember-flow-card-rejection phase 1
updated: 2026-09-11
---

### Phase 1: Rejection outcome stubs

#### Automated

- [ ] 1.1 Add Rejected, the ReviewOutcome alias and FINISHING_OUTCOMES in domain/remember/value_objects.py
- [ ] 1.2 Rename ReviewEvent.grade to outcome and widen it to ReviewOutcome
- [ ] 1.3 Add Sitting.guard_outcome and route GradeCardCommand's guard through it
- [ ] 1.4 Filter non-Grade outcomes out of SchedulingReplay.replay
- [ ] 1.5 Add domain/remember/outbox.py with CARD_REJECTED and CardRejectedPayload
- [ ] 1.6 Migrate the 21 ReviewEvent construction sites across src, unit, property and bdd suites

#### Manual

- [ ] 1.7 Grep domain/remember and application/remember for a surviving .grade and confirm only Scheduler's parameter remains

### Phase 2: Rejection settles a card and never reaches the scheduler

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Treat a rejection as finishing its card in is_finished and outstanding
- [ ] 2.2 Keep a rejected card out of next_card for the rest of the sitting
- [ ] 2.3 Return None from SchedulingReplay.replay for a log holding only rejections
- [ ] 2.4 Fold only the graded events when a card's log mixes grades and a rejection

### Phase 3: Rejection write-path stubs

#### Automated

- [ ] 3.1 Add outbox to remember's UnitOfWork port and to the in-memory unit of work
- [ ] 3.2 Add RejectCardCommand with no Scheduler dependency
- [ ] 3.3 Add POST /review-sittings/{sitting_id}/cards/{card_id}/rejection returning 204
- [ ] 3.4 Add get_reject_card_command in compose and thread the outbox store into the remember unit of work
- [ ] 3.5 Add the outbox store, appender and reject seam to InMemoryRememberComposition

#### Manual

- [ ] 3.6 Curl the rejection route against a running backend and confirm HTTP 204 with an empty body

### Phase 4: Reject command behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Refuse a rejection under each of the four conditions grading already refuses
- [ ] 4.2 Write the review event and the card_rejected envelope inside one unit of work
- [ ] 4.3 Leave the scheduling state repository untouched on a rejection

#### Manual

- [ ] 4.4 Curl a rejection then read /_outbox and confirm a card_rejected envelope that later reads consumed

### Phase 5: Distill discard stubs

#### Automated

- [ ] 5.1 Add CardRepository.get and implement it on the in-memory adapter
- [ ] 5.2 Add DiscardCardCommand taking card id, reason, detail and discarded_at
- [ ] 5.3 Add CardDiscardHandler bound to CARD_REJECTED
- [ ] 5.4 Register the discard command and handler in compose and in the worker's handler list
- [ ] 5.5 Add a worker seam to InMemoryRememberComposition over its own notes and cards repositories

### Phase 6: Distill discard behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Stamp a user_audit Discard carrying the envelope's rejected_at
- [ ] 6.2 No-op on a card that already carries any Discard
- [ ] 6.3 No-op on a card id that names no card
- [ ] 6.4 Log and ack a malformed card_rejected payload without calling the command

### Phase 7: Acceptance layer for AC-17 and AC-23

#### Automated

- [ ] 7.1 Register markers AC-16 through AC-23 in pyproject.toml

#### Manual

- [ ] 7.2 Author the AC-17 and AC-23 scenarios via /bdd
- [ ] 7.3 Confirm the new scenarios fail on assertions, not on undefined steps or collection
- [ ] 7.4 Confirm no existing remember-flow scenario regressed

### Phase 8: TUI client, store and binding stubs

#### Automated

- [ ] 8.1 Regenerate src/api/generated/schema.d.ts against the running backend
- [ ] 8.2 Add rejectCard with a 204 branch ahead of the data guard in src/api/sittings.ts
- [ ] 8.3 Add currentCard mapping PresentedCardDTO in src/api/sittings.ts
- [ ] 8.4 Add rejectCurrentCard to the sitting store and extend LastAction for retry
- [ ] 8.5 Bind the reject key in SittingOverlay behind isBackVisible and add its hint constant
- [ ] 8.6 Add rejectCard and currentCard to the six vi.mock factories over src/api/sittings

#### Manual

- [ ] 8.7 Run the TUI against a running backend and confirm reveal and the four grades behave as before

### Phase 9: Reject client and store behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Resolve rejectCard on a 204 and raise SittingHttpError on a client error
- [ ] 9.2 Re-read current-card after a rejection and apply the presented card to the store
- [ ] 9.3 Push the re-read partition through applyPartition so the poll cannot clobber it
- [ ] 9.4 Route a sitting_expired rejection into recoverFromSittingExpired

#### Manual

- [ ] 9.5 Reject a card in the running TUI and confirm the next card appears with no further keystroke

### Phase 10: Overlay gesture behind the reveal gate

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Fire the reject gesture only while the back is visible
- [ ] 10.2 Render the reject hint only alongside the back

#### Manual

- [ ] 10.3 Walk a sitting rejecting one card, open a new sitting, and confirm the card is not offered
