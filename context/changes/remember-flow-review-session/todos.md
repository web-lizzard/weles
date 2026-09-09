---
change_id: remember-flow-review-session
current_phase: 6
next_step: 6.1
next_command: /unit-test remember-flow-review-session phase 6
updated: 2026-09-10
---

### Phase 1: Extend the acceptance layer to the frame's behaviours

#### Manual

- [x] 1.1 Author the frame-derived scenarios under existing AC tags via /bdd — c70dfe1
- [x] 1.2 Confirm the remember-flow scenarios fail on assertions, not collection — c70dfe1

### Phase 2: Domain — membership and due-ness

#### Tests

- [x] tests generated — c80b813

#### Automated

- [x] 2.1 Fill ShowingLimit, Sitting validation, contains and visible — 64a1d18
- [x] 2.2 Give card_is_due a stamp parameter and treat a stale record as due — 64a1d18

#### Manual

- [x] 2.3 Check the stale-stamp case is asserted apart from the missing-record case — 64a1d18

### Phase 3: Domain — completion and ordering

#### Tests

- [x] tests generated — b0406e3

#### Automated

- [x] 3.1 Fill SittingCompletion over this sitting's grades — e3a9aa3
- [x] 3.2 Fill _eligible_pool and next_card with the foreign-event filter — e3a9aa3
- [x] 3.3 Fill sitting_seeded_draw as a pure function of sitting id and events — e3a9aa3

#### Manual

- [x] 3.4 Run the sitting suite twice and confirm the seeded draw picks the same card — e3a9aa3

#### Triage

- [x] 3.5 R1-F1 Foreign sitting events change the drawn next card (proof: 340db23) — 24dbe25

### Phase 4: Domain — reconstruction from the log

#### Tests

- [x] tests generated — 82ede50

#### Automated

- [x] 4.1 Fill SchedulingReplay.replay folding events in reviewed_at order — f20150c

#### Manual

- [x] 4.2 Confirm a replay of N events equals N sequential live reviews — f20150c

### Phase 5: Application — opening a sitting

#### Tests

- [x] tests generated — 2c7c5d1

#### Automated

- [x] 5.1 Fill OpenSittingCommand over the due set and the first front
- [x] 5.2 Inject the Scheduler so the command can read the live stamp

#### Manual

- [x] 5.3 Confirm the nothing-due case leaves the sitting repository untouched

### Phase 6: Application — revealing a back and rereading the current card

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Fill RevealBackQuery with its three not-found guards
- [ ] 6.2 Fill CurrentCardQuery so presentation survives a reread

#### Manual

- [ ] 6.3 Confirm two consecutive handles over one sitting return the same card

### Phase 7: Application — grading a card

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Fill the grade guards in order, ending at CardNotPresentableError
- [ ] 7.2 Capture reviewed_at once and save the event before the memoized state
- [ ] 7.3 Rebuild from the log when the memoized stamp does not match

#### Manual

- [ ] 7.4 Confirm the stale-stamp path uses the replayed state, not the memoized one

### Phase 8: In-memory adapters, unit of work, and port contracts

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Write the three in-memory remember repositories with snapshot and restore
- [ ] 8.2 Write the remember unit of work and the system clock
- [ ] 8.3 Write one behavioural contract suite per remember repository port

#### Manual

- [ ] 8.4 Confirm each contract suite reports its cases under the in_memory id

### Phase 9: The catalog onto distill

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Write InMemoryReviewCatalog over NoteRepository.list_all
- [ ] 9.2 Write the ReviewCatalog contract suite

#### Manual

- [ ] 9.3 Confirm a discarded card is absent from both catalog methods

### Phase 10: The FSRS scheduler adapter

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Pin fsrs==6.3.2 as a backend dependency
- [ ] 10.2 Write FsrsScheduler with the grade mapping and due_at outside the blob
- [ ] 10.3 Seed the fuzz from each event's own facts and restore the generator

#### Manual

- [ ] 10.4 Run the repeatability test twice and confirm the replayed due_at matches

### Phase 11: HTTP surface and composition

#### Tests

- [ ] tests generated

#### Automated

- [ ] 11.1 Write the four review-sitting routes returning application DTOs unmapped
- [ ] 11.2 Wire every remember seam in compose.py and include the router
- [ ] 11.3 Write the route tests for the happy loop and the 404 and 409 paths

#### Manual

- [ ] 11.4 Open a sitting over the running app and confirm a front with no back

### Phase 12: Migrate the acceptance steps onto the real adapters

#### Automated

- [ ] 12.1 Write InMemoryRememberComposition in the integration support package
- [ ] 12.2 Replace the step module's doubles with that composition
- [ ] 12.3 Move the AC-07 assertion from a multiplier to a growing interval

#### Manual

- [ ] 12.4 Confirm only _FixedClock survives in the step module
