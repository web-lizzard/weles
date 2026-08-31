---
change_id: capture-flow-socratic-conversation-send-mesage-refactor
current_phase: 5
next_step: 5.3
next_command: /implement capture-flow-socratic-conversation-send-mesage-refactor phase 5
updated: 2026-08-31
---

### Phase 1: `GenerateReplyCommand.guard_session` + self-loading `handle`

#### Tests

- [x] tests generated — f1766f5

#### Automated

- [x] 1.1 Add `guard_session` + `capture_sessions` param to `GenerateReplyCommand`; delete `load_open_session_for_turn` — b20a14f
- [x] 1.2 Change `handle` to `handle(session_id, content)`, loading and re-validating its own session; drop the R4-F1 re-read — b20a14f
- [x] 1.3 Wire `capture_sessions` into `compose.get_generate_reply_command` — b20a14f
- [x] 1.4 Rewire `get_turn_context` + route to depend on `get_generate_reply_command` and call `guard_session`/`handle` with `session_id` — b20a14f
- [x] 1.5 Update `tests/integration/support/in_memory_capture.py`'s override factory for the new constructor signature — b20a14f

#### Manual

- [x] 1.6 Curl unknown-session repro against dev server, confirm clean 404 JSON — b20a14f

### Phase 2: In-band `CoreException` → `ReplyErrorEvent`

#### Tests

- [x] tests generated — 5e72c73

#### Automated

- [x] 2.1 Add `ReplyErrorEvent` to `dto.py`, widen `ReplyStreamEvent` — 3771527
- [x] 2.2 Wrap `send_message` generator body in `try/except CoreException`, yield `ReplyErrorEvent` — 3771527

### Phase 3: TUI `stream.ts` — parse `error` events + richer pre-stream errors

#### Tests

- [x] tests generated — 0c3f0a6

#### Automated

- [x] 3.1 Add `ReplyErrorEvent`/widen union + `parseStreamEvent` handling in `stream.ts`
- [x] 3.2 Add `SendMessageHttpError`, parse JSON body on `!response.ok`

### Phase 4: TUI `chat.ts` store — `streamError` state

#### Tests

- [x] tests generated — 747668d

#### Automated

- [x] 4.1 Add `streamError` state + clear-on-send in `chat.ts` — 3143087
- [x] 4.2 Catch in-band error event and thrown `SendMessageHttpError`/fallback in `sendUserMessage` — 3143087

### Phase 5: TUI `CaptureScreen.tsx` — status-bar rendering

#### Tests

- [x] tests generated — d22c7f4

#### Automated

- [x] 5.1 Add `StatusBar` component and wire `streamError` into `CaptureScreen` — 9d17052
- [x] 5.2 Adjust `shouldShowWelesBrand` row-budget math for the error block — 9d17052

#### Manual

- [ ] 5.3 Run built TUI + dev backend, send a normal message, confirm no layout regression
