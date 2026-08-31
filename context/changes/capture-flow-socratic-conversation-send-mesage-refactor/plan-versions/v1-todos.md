---
change_id: capture-flow-socratic-conversation-send-mesage-refactor
current_phase: 1
next_step: 1.1
next_command: /unit-test capture-flow-socratic-conversation-send-mesage-refactor phase 1
updated: 2026-08-31
---

### Phase 1: `GenerateReplyCommand.load_turn` — move ownership + Depends wiring

#### Tests

- [ ] tests generated

#### Automated

- [ ] 1.1 Add `load_turn` method + `capture_sessions` param to `GenerateReplyCommand`; delete `load_open_session_for_turn`
- [ ] 1.2 Wire `capture_sessions` into `compose.get_generate_reply_command`
- [ ] 1.3 Rewire `get_turn_context` to depend on `get_generate_reply_command` and call `load_turn`
- [ ] 1.4 Update `tests/integration/support/in_memory_capture.py`'s override factory for the new constructor signature

#### Manual

- [ ] 1.5 Curl unknown-session repro against dev server, confirm clean 404 JSON

### Phase 2: Remove the R4-F1 staleness re-read in `handle`

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Remove R4-F1 in-UoW staleness re-read in `handle`, add explanatory comment

### Phase 3: In-band `CoreException` → `ReplyErrorEvent`

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 Add `ReplyErrorEvent` to `dto.py`, widen `ReplyStreamEvent`
- [ ] 3.2 Wrap `send_message` generator body in `try/except CoreException`, yield `ReplyErrorEvent`

### Phase 4: TUI `stream.ts` — parse `error` events + richer pre-stream errors

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Add `ReplyErrorEvent`/widen union + `parseStreamEvent` handling in `stream.ts`
- [ ] 4.2 Add `SendMessageHttpError`, parse JSON body on `!response.ok`

### Phase 5: TUI `chat.ts` store — `streamError` state

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 Add `streamError` state + clear-on-send in `chat.ts`
- [ ] 5.2 Catch in-band error event and thrown `SendMessageHttpError`/fallback in `sendUserMessage`

### Phase 6: TUI `CaptureScreen.tsx` — status-bar rendering

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Add `StatusBar` component and wire `streamError` into `CaptureScreen`
- [ ] 6.2 Adjust `shouldShowWelesBrand` row-budget math for the error block

#### Manual

- [ ] 6.3 Run built TUI + dev backend, send a normal message, confirm no layout regression
