---
change_id: remember-flow-session-resume
current_phase: 4
next_step: 4.1
next_command: /implement remember-flow-session-resume phase 4
updated: 2026-09-10
---

### Phase 1: Acceptance layer for AC-10 through AC-13

#### Manual

- [x] 1.1 Add advance to _FixedClock and a resume_horizon seam on the test composition
- [x] 1.2 Author the AC-10/AC-11 and AC-12/AC-13 scenarios via /bdd
- [x] 1.3 Confirm the new scenarios fail on assertions, not collection
- [x] 1.4 Confirm the clock change breaks no existing remember-flow scenario

### Phase 2: Settings and composition wiring

#### Automated

- [x] 2.1 Add sitting_resume_horizon_hours to Settings — ce033a3
- [x] 2.2 Compose ResumeHorizon and pass it to OpenSittingCommand — ce033a3

#### Manual

- [x] 2.3 Check a zero horizon is refused by the VO at compose time — ce033a3

### Phase 3: Convergent open returns a resumable sitting

#### Tests

- [x] tests generated — c56163b

#### Automated

- [x] 3.1 Return a resumed sitting from the convergent branch of handle — 955cfc0
- [x] 3.2 Replace the inline due comprehension with due_card_ids — 955cfc0

#### Manual

- [x] 3.3 Confirm two consecutive opens return the same sitting marked resumed — 955cfc0

### Phase 4: Expiry stubs

#### Automated

- [ ] 4.1 Add SittingExpiredError and map sitting_expired to 409
- [ ] 4.2 Give CurrentCardQuery and RevealBackQuery a Clock parameter
- [ ] 4.3 Pass the clock from the production and test compositions

### Phase 5: Expiry refuses work by sitting id

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 Refuse an expired sitting in _guard_grade before any write
- [ ] 5.2 Refuse an expired sitting in both read handlers

#### Manual

- [ ] 5.3 Confirm all three by-id routes return 409 sitting_expired past the horizon

### Phase 6: TUI API client stubs

#### Automated

- [ ] 6.1 Add ResumedSitting, SITTING_EXPIRED and outstandingCount to the client types

#### Manual

- [ ] 6.2 Regenerate schema.d.ts against a running backend

### Phase 7: TUI API client behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Accept the resumed kind and map outstanding_count in openSitting
- [ ] 7.2 Map outstanding_count in gradeCard

### Phase 8: TUI store stubs

#### Automated

- [ ] 8.1 Add isResumed, outstandingCount and notice to the store state

### Phase 9: TUI store behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Record the resume marker and the live outstanding count
- [ ] 9.2 Recover from sitting_expired by re-opening with a notice

### Phase 10: Overlay shows the return, the count, and the expiry

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Render the resumed marker, the outstanding count and the notice

#### Manual

- [ ] 10.2 Walk resume and expiry recovery in the TUI against a live backend
