---
change_id: capture-flow-socratic-conversation
current_phase: 11
next_step: 11.0
next_command: /unit-test capture-flow-socratic-conversation phase 11
updated: 2026-08-31
---

### Phase 1: Domain model — stubs

#### Automated

- [x] 1.1 Create `domain/capture/value_objects.py` — Topic, MessageContent, MessageRole, SessionId, MessageId, SessionStatus (structure only) — 7d6d619
- [x] 1.2 Create `domain/capture/capture_session.py` — CaptureSession shape + start()/assign_topic() signatures — 7d6d619
- [x] 1.3 Create `domain/capture/message.py` — Message shape + record() signature — 7d6d619
- [x] 1.4 Create `domain/capture/ports.py` — CaptureSessionRepository, MessageRepository Protocols — 7d6d619
- [x] 1.5 Create `domain/capture/exceptions.py` — VO and aggregate-guard exceptions — 7d6d619

### Phase 2: Domain model — behavior

#### Tests

- [x] tests generated — 774a209

#### Automated

- [x] 2.1 Implement VO validators (non-empty + length caps) in `model_validator(mode="after")`, raising CoreException subclasses directly — no `Field(min_length=/max_length=)` — e4ad6bc
- [x] 2.2 Implement CaptureSession.start()/assign_topic() — e4ad6bc
- [x] 2.3 Implement Message.record() — e4ad6bc
- [x] 2.4 `uv run pytest tests/unit/capture/test_value_objects.py tests/unit/capture/test_model.py -v` green — e4ad6bc

### Phase 3: Application ports & in-memory adapters — stubs

#### Automated

- [x] 3.1 Create `application/capture/value_objects.py` — TranscriptEntry, ConfidencePointKind, ConfidencePoint, ConfidenceAssessment — 08e9fb4
- [x] 3.2 Create `application/capture/exceptions.py` — EmptyConfidencePointError — 08e9fb4
- [x] 3.3 Create `application/capture/ports.py` — TopicExtractionPort, ConfidenceAssessmentPort, ReplyGenerationPort, UnitOfWork — 08e9fb4
- [x] 3.4 Create `application/capture/queries/transcript.py` — TranscriptQueryPort — 08e9fb4
- [x] 3.5 Create `adapters/out/in_memory/capture/` module shells (store, both repos, transcript query, unit of work, 3 stand-in adapters) — 08e9fb4

### Phase 4: Application ports & in-memory adapters — behavior

#### Tests

- [x] tests generated — c540593

#### Automated

- [x] 4.1 Implement ConfidencePoint validation (manual, no `Field(min_length=...)`) — 26d6ae7
- [x] 4.2 Implement InMemoryMessageStore, InMemoryCaptureSessionRepository, InMemoryMessageRepository, InMemoryTranscriptQueryAdapter (shared store) — 26d6ae7
- [x] 4.3 Implement InMemoryUnitOfWork with snapshot-on-enter / restore-on-rollback — 26d6ae7
- [x] 4.4 Implement DeterministicTopicExtractionAdapter, DeterministicConfidenceAssessmentAdapter, DeterministicReplyGenerationAdapter — 26d6ae7
- [x] 4.5 Write contract-test suites for all 6 ports (parametrized, in-memory only) — c540593
- [x] 4.6 `uv run pytest tests/unit/capture -v` green — 26d6ae7

### Phase 5: Application commands — stubs

#### Automated

- [x] 5.1 Create `application/capture/dto.py` — StartCaptureSessionResponseDTO, SendMessageRequestDTO, ReplyDeltaEvent, ReplyDoneEvent, ReplyStreamEvent
- [x] 5.2 Create `application/capture/commands/start_capture_session.py` — StartCaptureSessionCommand shell
- [x] 5.3 Create `application/capture/commands/send_message.py` — load_open_session_for_turn + GenerateReplyCommand shells

### Phase 6: Application commands — behavior

#### Tests

- [x] tests generated — 427df3c

#### Automated

- [x] 6.1 Implement StartCaptureSessionCommand.handle() — 6e7de42
- [x] 6.2 Implement load_open_session_for_turn() — content validation, session lookup/guard, no write, no UnitOfWork — 6e7de42
- [x] 6.3 Implement GenerateReplyCommand.handle() — one UnitOfWork: lazy topic assignment, streamed reply, agent-message persist, single commit, done event — 6e7de42
- [x] 6.4 Write unit tests: load_open_session_for_turn raises exact CoreException subclass for not-found/closed/invalid-content; GenerateReplyCommand — first-turn lazy-start, second-turn skip, commit-after-drain (one commit), rollback-on-cancel — 6e7de42
- [x] 6.5 `uv run pytest tests/unit/capture -v` green — 6e7de42

### Phase 7: HTTP adapter — stubs

#### Automated

- [x] 7.1 Create `adapters/http/capture.py` — route signatures for both endpoints, incl. `get_turn_context` Depends wrapper, not yet wired — 73a67df
- [x] 7.2 Extend `adapters/http/errors.py:EXCEPTION_STATUS_MAP` with capture-specific codes — 73a67df

### Phase 8: HTTP adapter — behavior

#### Tests

- [x] tests generated — 32406f0

#### Automated

- [x] 8.1 Wire composition root (shared store/repos/adapters/commands, get_turn_context) via FastAPI Depends — e0acf77
- [x] 8.2 Register capture router in `main.py` — e0acf77
- [x] 8.3 Write integration tests via httpx.ASGITransport (creation, first-turn stream, second-turn stream, clean 404 for unknown session, clean 422 for empty content — both via the Depends chain, not a broken stream) — e0acf77
- [x] 8.4 `uv run pytest tests/integration -v` green — e0acf77

#### Manual

- [x] 8.5 Run the dev server and curl both endpoints, eyeball the SSE stream — e0acf77

### Phase 9: Acceptance scenarios (BDD, AC-01–AC-04)

#### Automated

- [x] 9.1 Write `tests/features/capture-flow/US-01-socratic-conversation.feature` (AC-01–AC-04, tagged) — a889204
- [x] 9.2 Write `tests/bdd/steps/capture.py`, import from `tests/bdd/test_features.py` — a889204
- [x] 9.3 `uv run pytest tests/bdd -m "capture-flow and (AC-01 or AC-02 or AC-03 or AC-04)" -v` green — a889204

### Phase 10: TUI data layer — stubs

#### Automated

- [x] 10.1 Create `tui/src/api/stream.ts` — ReplyStreamEvent types + function signatures
- [x] 10.2 Create `tui/src/store/chat.ts` — useChatStore shape/action signatures
- [x] 10.3 Run `pnpm generate:api` against a running dev backend; verify SSE route codegen, fall back to hand-declared types if unusable

### Phase 11: TUI data layer — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 11.1 Implement SSE parsing in stream.ts (ReadableStream + TextDecoderStream)
- [ ] 11.2 Implement startCaptureSession/sendMessage
- [ ] 11.3 Implement useChatStore reducer logic
- [ ] 11.4 Write Vitest unit tests: SSE parser (fake ReadableStream), store reducer
- [ ] 11.5 `pnpm --dir tui test` green

### Phase 12: TUI chat screen — stubs

#### Automated

- [ ] 12.1 Add `ink-text-input` dependency
- [ ] 12.2 Create `tui/src/screens/CaptureScreen.tsx` — component shell
- [ ] 12.3 Update `tui/src/app.tsx` to render CaptureScreen

### Phase 13: TUI chat screen — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 13.1 Wire CaptureScreen to useChatStore + api/stream.ts (Static transcript, live reply line, TextInput)
- [ ] 13.2 Write ink-testing-library interaction tests (submit, incremental deltas, final transcript, topic update)
- [ ] 13.3 `pnpm --dir tui test` green

#### Manual

- [ ] 13.4 Build and run the TUI CLI against the running backend; hold a real multi-turn conversation
