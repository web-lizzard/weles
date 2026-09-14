---
change_id: tui-capture-screen-fixes
current_phase: 9
next_step: 9.1
next_command: /implement tui-capture-screen-fixes phase 9
updated: 2026-09-14
---

### Phase 1: Markdown renderer stubs

#### Automated

- [x] 1.1 Type check passes — e6a9723
- [x] 1.2 Lint passes — e6a9723
- [x] 1.3 Existing suite stays green — e6a9723

### Phase 2: Markdown renderer behavior

#### Tests

- [x] tests generated — 2c93fa9

#### Automated

- [x] 2.1 Markdown renderer tests pass — c899895
- [x] 2.2 Type check passes — c899895
- [x] 2.3 Lint passes — c899895

### Phase 3: Capture layout stubs

#### Automated

- [x] 3.1 Type check passes — ad16d43
- [x] 3.2 Lint passes — ad16d43
- [x] 3.3 Existing suite stays green — ad16d43

### Phase 4: Capture layout behavior

#### Tests

- [x] tests generated — 7b4029c

#### Automated

- [x] 4.1 Capture layout tests pass — d7330ec
- [x] 4.2 Type check passes — d7330ec
- [x] 4.3 Lint passes — d7330ec

### Phase 5: Chat store stubs

#### Automated

- [x] 5.1 Type check passes — f036027
- [x] 5.2 Lint passes — f036027
- [x] 5.3 Existing suite stays green — f036027

### Phase 6: Chat store behavior

#### Tests

- [x] tests generated — 1d0b33f

#### Automated

- [x] 6.1 Chat store tests pass — 65ffd84
- [x] 6.2 Type check passes — 65ffd84
- [x] 6.3 Lint passes — 65ffd84

### Phase 7: Activity indicator stubs

#### Automated

- [x] 7.1 Type check passes — 5c17072
- [x] 7.2 Lint passes — 5c17072
- [x] 7.3 Existing suite stays green — 5c17072

### Phase 8: Activity indicator behavior

#### Tests

- [x] tests generated — 8cf7dc5

#### Automated

- [x] 8.1 Activity indicator tests pass
- [x] 8.2 Type check passes
- [x] 8.3 Lint passes

### Phase 9: Capture shell stubs

#### Automated

- [ ] 9.1 Type check passes
- [ ] 9.2 Lint passes
- [ ] 9.3 Existing suite stays green

### Phase 10: Capture shell behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Capture screen tests pass
- [ ] 10.2 Full TUI suite passes
- [ ] 10.3 Type check passes
- [ ] 10.4 Lint passes

#### Manual

- [ ] 10.5 Long conversation scrolls into terminal history without overdrawing the frame
- [ ] 10.6 Long markdown reply streams formatted with the activity indicator ticking
- [ ] 10.7 Approve hint shows with a draft and /approve clears screen and scrollback

### Phase 11: Draft region stubs

#### Automated

- [ ] 11.1 Type check passes
- [ ] 11.2 Lint passes
- [ ] 11.3 Existing suite stays green

### Phase 12: Draft region behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 12.1 Capture screen tests pass
- [ ] 12.2 Full TUI suite passes
- [ ] 12.3 Type check passes
- [ ] 12.4 Lint passes

#### Manual

- [ ] 12.5 Long draft is pinned at the top and scrolls with up and down arrows
- [ ] 12.6 Redraft keeps the draft pinned while the reply flows under it
- [ ] 12.7 Touchpad history scroll moves the draft and it returns at the bottom

### Phase 13: Bottom panel stubs

#### Automated

- [ ] 13.1 Type check passes
- [ ] 13.2 Lint passes
- [ ] 13.3 Existing suite stays green

### Phase 14: Bottom panels behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 14.1 Panel tests pass
- [ ] 14.2 Full TUI suite passes
- [ ] 14.3 Type check passes
- [ ] 14.4 Lint passes

#### Manual

- [ ] 14.5 Notes panel replaces the input and scrolls a long formatted note
- [ ] 14.6 Sitting panel scrolls a long card and source view within the terminal
- [ ] 14.7 Resizing with a panel open keeps it within the terminal height
