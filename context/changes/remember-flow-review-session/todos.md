---
change_id: remember-flow-review-session
current_phase: 15
next_step: 15.4
next_command: /implement remember-flow-review-session phase 15
updated: 2026-09-10
---

### Phase 1: Extend the acceptance layer to the frame's behaviours

#### Manual

- [x] 1.1 Author the frame-derived scenarios under existing AC tags via /bdd — c70dfe1
- [x] 1.2 Confirm the remember-flow scenarios fail on assertions, not collection — c70dfe1

#### Triage

- [x] 1.3 R4-F1 Four remember-flow step phrases resolve under no registered keyword (proof: cb66884) — c56f18d
- [x] 1.4 R4-F3 The card-in-front step asserts the outcome of a seeded coin flip (proof: cb66884) — 66cb8aa

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
- [x] 3.6 R2-F1 Eligible pool must exclude members above the minimum showing count — 7e4321b
- [x] 3.7 R2-F2 Draw seed must incorporate the sitting id — 7e4321b
- [x] 3.8 R2-F3 Draw seed must sort events before hashing — 7e4321b
- [x] 3.9 R2-F4 Draw seed must incorporate each event's card id — 7e4321b
- [x] 3.10 R2-F5 Draw seed must use eight big-endian digest bytes — 7e4321b

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

- [x] 5.1 Fill OpenSittingCommand over the due set and the first front — 653356a
- [x] 5.2 Inject the Scheduler so the command can read the live stamp — 653356a

#### Manual

- [x] 5.3 Confirm the nothing-due case leaves the sitting repository untouched — 653356a

### Phase 6: Application — revealing a back and rereading the current card

#### Tests

- [x] tests generated — 95e745d

#### Automated

- [x] 6.1 Fill RevealBackQuery with its three not-found guards — 05a0782
- [x] 6.2 Fill CurrentCardQuery so presentation survives a reread — 05a0782

#### Manual

- [x] 6.3 Confirm two consecutive handles over one sitting return the same card — 05a0782

#### Triage

- [x] 6.4 R4-F4 CurrentCardQuery raises instead of reporting sitting_complete on the DTO (proof: cb66884)

### Phase 7: Application — grading a card

#### Tests

- [x] tests generated — 8920945

#### Automated

- [x] 7.1 Fill the grade guards in order, ending at CardNotPresentableError — 8db7fc5
- [x] 7.2 Capture reviewed_at once and save the event before the memoized state — 8db7fc5
- [x] 7.3 Rebuild from the log when the memoized stamp does not match — 8db7fc5

#### Manual

- [x] 7.4 Confirm the stale-stamp path uses the replayed state, not the memoized one — aa65e20

#### Triage

- [ ] 7.5 R4-F5 The grade write saves event and scheduling state concurrently, not in order — DISMISSED: the TaskGroup concurrency is a deliberate decision, not a defect

### Phase 8: In-memory adapter stubs

#### Automated

- [x] 8.1 Create the remember in-memory adapter package — 2ace364
- [x] 8.2 Write the three repository classes as signatures with `...` bodies — 2ace364
- [x] 8.3 Write the unit of work and system clock as signatures with `...` bodies — 2ace364

#### Manual

- [x] 8.4 Confirm every method body in the new package is still `...` — 2ace364

### Phase 9: Fill the in-memory adapters, the unit of work, and the port contracts

#### Tests

- [x] tests generated — 6c316a6

#### Automated

- [x] 9.1 Fill the three in-memory remember repositories with snapshot and restore — 546ab61
- [x] 9.2 Fill the remember unit of work with a shared asyncio.Lock, and the system clock — 546ab61
- [x] 9.3 Write one behavioural contract suite per remember repository port — 6c316a6

#### Manual

- [x] 9.4 Confirm each contract suite reports its cases under the in_memory id — 546ab61
- [x] 9.5 Confirm a second UoW waits on the shared lock until the first window exits — 546ab61

### Phase 10: Review catalog stub

#### Automated

- [x] 10.1 Write InMemoryReviewCatalog as a signature with `...` bodies — 5dacaaf

#### Manual

- [x] 10.2 Confirm both catalog method bodies are still `...` — 5dacaaf

### Phase 11: Fill the catalog and its contract suite

#### Tests

- [x] tests generated — 26f8f1b

#### Automated

- [x] 11.1 Fill InMemoryReviewCatalog over NoteRepository.list_all — e78791c
- [x] 11.2 Write the ReviewCatalog contract suite — e78791c

#### Manual

- [x] 11.3 Confirm a discarded card is absent from both catalog methods

### Phase 12: FSRS dependency and scheduler stub

#### Automated

- [x] 12.1 Pin fsrs==6.3.2 as a backend dependency and run uv sync — 9866f4e
- [x] 12.2 Write FsrsScheduler as a signature with `...` bodies — 9866f4e

#### Manual

- [x] 12.3 Confirm uv.lock records fsrs==6.3.2 and both bodies are still `...` — 9866f4e

### Phase 13: Fill the FSRS scheduler and prove repeatability

#### Tests

- [x] tests generated — f8261d1

#### Automated

- [x] 13.1 Fill FsrsScheduler with the grade mapping and due_at outside the blob — 4020add
- [x] 13.2 Seed the fuzz from each event's own facts and restore the generator — 4020add

#### Manual

- [x] 13.3 Run the repeatability test twice and confirm the replayed due_at matches — 4020add

### Phase 14: HTTP and composition stubs

#### Automated

- [x] 14.1 Write the four review-sitting route signatures with `...` bodies — 6709cf2
- [x] 14.2 Declare the four remember providers and the UoW factory in compose.py — 6709cf2
- [x] 14.3 Include the remember router in main.py — 6709cf2

#### Manual

- [x] 14.4 Confirm the four routes appear in /docs while their bodies are still `...` — fe93f8d

### Phase 15: Fill the HTTP surface and composition

#### Tests

- [x] tests generated — 817e596

#### Automated

- [x] 15.1 Fill the four routes returning application DTOs unmapped — e550265
- [x] 15.2 Wire every remember seam in compose.py over one shared lock — e550265
- [x] 15.3 Write the route tests for the happy loop and the 404 and 409 paths — 817e596

#### Manual

- [ ] 15.4 Open a sitting over the running app and confirm a front with no back

#### Triage

- [x] 15.5 R4-F2 The whole-suite gate `uv run pytest` exits non-zero at phase 15 — b4ceab0

### Phase 16: Migrate the acceptance steps and the handler unit tests onto the real adapters

#### Automated

- [x] 16.1 Write InMemoryRememberComposition in the integration support package — 4e296eb
- [x] 16.2 Replace the step module's doubles with that composition — 4e296eb
- [x] 16.3 Move the AC-07 assertion from a multiplier to a growing interval — 4e296eb
- [x] 16.4 Add tests/unit/remember/conftest.py with the shared handler fixtures and builders — 4e296eb
- [x] 16.5 Repoint the four handler unit-test modules onto the real in-memory adapters — 4e296eb
- [x] 16.6 Drive the handler tests through FsrsScheduler except where a value must be forced — 4e296eb
- [x] 16.7 Assert one commit on the happy path and no leaked write past an exception — 4e296eb

#### Manual

- [x] 16.8 Confirm only _FixedClock survives in the step module — 0d3574b
- [x] 16.9 Confirm every surviving double under tests/unit/remember is named for what it forces — 0d3574b
