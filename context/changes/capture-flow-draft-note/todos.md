---
change_id: capture-flow-draft-note
current_phase: 8
next_step: 8.1
next_command: /implement capture-flow-draft-note phase 8
updated: 2026-09-01
---

### Phase 1: Rename `Topic` to `SessionTopic`

#### Automated

- [x] 1.1 Rename `Topic` → `SessionTopic`, `TOPIC_MAX_LENGTH` → `SESSION_TOPIC_MAX_LENGTH`, `EmptyTopicError` → `EmptySessionTopicError`, `TopicTooLongError` → `SessionTopicTooLongError` — `domain/capture/value_objects.py`, `domain/capture/exceptions.py` — 2572cd4
- [x] 1.2 Follow the rename through `CaptureSession`, `TopicExtractionPort`, `GenerateReplyCommand`, `DeterministicTopicExtractionAdapter` — 2572cd4
- [x] 1.3 Update `EXCEPTION_STATUS_MAP` keys to `empty_session_topic` and `session_topic_too_long` — `adapters/http/errors.py` — 2572cd4
- [x] 1.4 Update every test referencing the old name: unit, contract, and BDD step modules — 2572cd4
- [x] 1.5 `cd backend && uv run pytest`, `uv run ruff check src tests`, `uv run basedpyright` all clean — 2572cd4

### Phase 2: Domain vocabulary and aggregates — stubs

#### Automated

- [x] 2.1 Add `NoteStatus`, `Label`, `Embedding`, `NoteContent`, `NoteId`, `TopicId`, `TagId` and the two length constants — `domain/capture/value_objects.py` — 2ee7327
- [x] 2.2 Add `EmptyLabelError`, `LabelTooLongError`, `EmptyEmbeddingError`, `EmptyNoteContentError`, `NoteContentTooLongError`, `SessionNoteAlreadyDraftedError` — `domain/capture/exceptions.py` — 2ee7327
- [x] 2.3 Add `Topic` and `Tag` aggregates with `mint()` raising `NotImplementedError` — `domain/capture/topic.py`, `domain/capture/tag.py` — 2ee7327
- [x] 2.4 Add `Note` aggregate with `draft()` raising `NotImplementedError` — `domain/capture/note.py` — 2ee7327
- [x] 2.5 Add `note_id: NoteId | None` and the `draft_note()` signature to `CaptureSession` — 2ee7327
- [x] 2.6 Add `NoteRepository`, `TopicRepository`, `TagRepository` protocols — `domain/capture/ports.py` — 2ee7327

### Phase 3: Domain vocabulary and aggregates — behavior

#### Tests

- [x] tests generated — cb07401

#### Automated

- [x] 3.1 Implement the `Label`, `Embedding` and `NoteContent` validators
- [x] 3.2 Implement `Topic.mint`, `Tag.mint` and `Note.draft` (extracting `topic_id` and `tag_ids`)
- [x] 3.3 Implement `CaptureSession.draft_note()` with the closed-session and already-drafted guards
- [x] 3.4 Add the six new codes to `EXCEPTION_STATUS_MAP` — `adapters/http/errors.py`
- [x] 3.5 Write unit tests: value-object validation, the three factories, both guards, exception-mapping exhaustiveness
- [x] 3.6 `cd backend && uv run pytest` green

### Phase 4: Chunk protocol and SSE events — stubs

#### Automated

- [x] 4.1 Add `ReplyChunkKind` and the four chunk classes under `Field(discriminator="kind")` — `application/capture/value_objects.py` — d431c49
- [x] 4.2 Retype `ReplyGenerationPort.generate`, add `EmbeddingPort`, add `notes`/`topics`/`tags` to `UnitOfWork` — `application/capture/ports.py` — d431c49
- [x] 4.3 Add `DraftTopicEvent`, `DraftTagEvent`, `DraftDeltaEvent`, `DraftDoneEvent` to the `ReplyStreamEvent` union — `application/capture/dto.py` — d431c49
- [x] 4.4 Wrap the deterministic adapter's output in `ReplyTextChunk` and read `chunk.text` in `GenerateReplyCommand` — d431c49
- [x] 4.5 Update `test_reply_generation_contract.py` to join `chunk.text` — d431c49

### Phase 5: Deterministic draft adapter — behavior

#### Tests

- [x] tests generated — f0abf27

#### Automated

- [x] 5.1 Add the confirmation-phrase set and the drafting branch to `DeterministicReplyGenerationAdapter` (`reply` → `topic` → `tag`* → `note`*) — eecf429
- [x] 5.2 Write contract-test assertions for chunk kinds and stream ordering, both for a drafting and a non-drafting transcript — f0abf27
- [x] 5.3 `cd backend && uv run pytest` green — eecf429

### Phase 6: In-memory persistence and UnitOfWork — stubs

#### Automated

- [x] 6.1 Add `InMemoryNoteRepository`, `InMemoryTopicRepository`, `InMemoryTagRepository` skeletons with `add`/`get`/`snapshot`/`restore` — 5db94a2
- [x] 6.2 Add the `DeterministicEmbeddingAdapter` skeleton — `adapters/out/in_memory/capture/embedding.py` — 5db94a2
- [x] 6.3 Extend `InMemoryUnitOfWork` with the three repositories and their snapshot/restore hooks — 5db94a2
- [x] 6.4 Wire the new adapters into `adapters/compose.py` — 5db94a2
- [x] 6.5 Wire the new adapters into `InMemoryCaptureComposition` — `tests/integration/support/in_memory_capture.py` — 5db94a2

### Phase 7: In-memory persistence and UnitOfWork — behavior

#### Tests

- [x] tests generated — 1391687

#### Automated

- [x] 7.1 Implement the three repository adapters (dict-backed, deep-copy snapshots) — d756eff
- [x] 7.2 Implement `DeterministicEmbeddingAdapter.embed` — d756eff
- [x] 7.3 Implement `InMemoryUnitOfWork` snapshot/restore across all five stores — d756eff
- [x] 7.4 Write contract suites for `NoteRepository`, `TopicRepository`, `TagRepository` and `EmbeddingPort` — d756eff
- [x] 7.5 Write the `InMemoryUnitOfWork` rollback test covering notes, topics and tags — d756eff
- [x] 7.6 `cd backend && uv run pytest` green — d756eff

### Phase 8: Vocabulary resolver and command routing — stubs

#### Automated

- [ ] 8.1 Add `VocabularyResolver` with `resolve_topic` and `resolve_tag` signatures — `application/capture/services/vocabulary.py`
- [ ] 8.2 Add the `vocabulary` dependency and the per-kind dispatch skeleton to `GenerateReplyCommand`
- [ ] 8.3 Construct and inject the resolver in `adapters/compose.py` and `InMemoryCaptureComposition`

### Phase 9: Vocabulary resolver and command routing — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Implement `VocabularyResolver.resolve_topic` and `resolve_tag` (embed, mint, persist)
- [ ] 9.2 Implement chunk routing in `GenerateReplyCommand.handle()`, emitting `draft_topic`/`draft_tag` only after resolution
- [ ] 9.3 Implement draft assembly: `session.draft_note()`, note and session saves, `DraftDoneEvent` built before `commit()`, draft-then-done yielded after the block
- [ ] 9.4 Write unit tests: event sequence, persisted note shape and `session.note_id`, mid-stream rollback, second-confirmation error, unchanged conversation path
- [ ] 9.5 `cd backend && uv run pytest` green

### Phase 10: HTTP integration and acceptance scenarios (AC-08, AC-09)

#### Automated

- [ ] 10.1 Write the SSE sequence integration test — `tests/integration/test_capture_http.py`
- [ ] 10.2 Write `tests/features/capture-flow/US-04-draft-note.feature` with the `@AC-08` and `@AC-09` scenarios
- [ ] 10.3 Write `tests/bdd/steps/draft_note.py` and register `bdd.steps.draft_note` in `pytest_plugins`
- [ ] 10.4 Add the `AC-05` through `AC-09` markers to `[tool.pytest.ini_options]` — `backend/pyproject.toml`
- [ ] 10.5 `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-08 or AC-09)" -v` green

#### Manual

- [ ] 10.6 Run the backend and curl one conversational turn and one confirmation turn; read the SSE frames

### Phase 11: TUI data layer — stubs

#### Automated

- [ ] 11.1 Add `DraftTopicEvent`, `DraftTagEvent`, `DraftDeltaEvent`, `DraftDoneEvent` and their `RawReplyStreamEvent` variants — `tui/src/api/stream.ts`
- [ ] 11.2 Add the `Draft` type and `draft: Draft | null` to `ChatState` — `tui/src/store/chat.ts`

### Phase 12: TUI data layer — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 12.1 Implement the four new branches in `parseStreamEvent`
- [ ] 12.2 Implement the store reducers, including reset on a new turn and on `streamError`
- [ ] 12.3 Write Vitest tests for the parser and for a full drafting sequence through the store
- [ ] 12.4 `pnpm --dir tui test` green

### Phase 13: TUI screen — stubs

#### Automated

- [ ] 13.1 Add `DraftNotePanel` returning `null`, wired between the transcript `Box` and `CoverageBanner` — `tui/src/screens/CaptureScreen.tsx`

### Phase 14: TUI screen — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 14.1 Implement `DraftNotePanel`: topic heading, tag line, body, each appearing as its part arrives
- [ ] 14.2 Extend `shouldShowWelesBrand` with a `hasDraft` argument and a `draftBlock` term
- [ ] 14.3 Write `ink-testing-library` tests for the panel states and the row budget
- [ ] 14.4 `pnpm --dir tui test`, `pnpm --dir tui typecheck`, `pnpm --dir tui lint` all clean

#### Manual

- [ ] 14.5 Run the backend and the TUI together, hold a short conversation, type a confirmation phrase and watch the panel fill with topic, then tags, then body
