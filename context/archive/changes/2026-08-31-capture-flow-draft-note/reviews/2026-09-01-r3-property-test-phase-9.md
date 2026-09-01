# Property test review — capture-flow-draft-note phase 9

ran at 2d355ba

| Field | Value |
| --- | --- |
| change-id | capture-flow-draft-note |
| scope | phase 9 |
| engine | Hypothesis 6.165.10 (pytest host, per `context/foundation/test-stack.md`) |
| date | 2026-09-01 |
| max_examples | 100–200 per property |
| vector | input-space / boundary |

## Oracle-able surface

- `backend/src/application/capture/services/vocabulary.py` — `VocabularyResolver.resolve_topic`, `resolve_tag`
- `backend/src/application/capture/commands/send_message.py` — `GenerateReplyCommand.handle` draft routing and assembly

## Properties hunted

1. **Resolver persistence** — `resolve_topic` / `resolve_tag` return an aggregate whose label and embedding match the input label and `embed(label.value)`, and the aggregate is retrievable from the repository.
2. **Fresh mint** — repeated `resolve_topic` calls with the same label mint distinct ids (no silent reuse).
3. **Draft-done fidelity** — `DraftDoneEvent.content` equals the persisted `Note.content.value` after a drafting turn.
4. **Draft-done tag order** — `DraftDoneEvent.tags` matches the ordered `DraftTagEvent` labels emitted on the stream.
5. **Malformed stream guard** — a drafting turn whose chunks include `draft_tag` or `draft_content` without a preceding `draft_topic` raises `CoreException`, not `AssertionError`.
6. **Empty-body rejection** — whitespace-only accumulated draft body raises `EmptyNoteContentError` with rollback (classified if rollback holds).

## Specimens

### R3-F1 — WARNING

- **Property** — `DraftDoneEvent.content` must equal the persisted note's canonical content after `NoteContent` stripping.
- **Shrunk input** — `DraftContentChunk(text=' 0 ')` (minimal padding around non-empty core; reproduces with `body='  padded body  '`).
- **Replay** — Hypothesis failing example: `core='0', pad_left=' ', pad_right=' '` → accumulated body `' 0 '`.
- **Proposed pin** — `test_R3_F1_draft_done_content_matches_persisted_note_content` in `backend/tests/unit/capture/test_send_message_command.py`.
- **Evidence** — proof-test skipped: HEAD on default branch
- **Fix:** the shrunk padded body (`' 0 '` / `'  padded body  '`) must make `draft_done.content == note.content.value` in the example suite until fixed, then remain as regression.

### R3-F2 — WARNING

- **Property** — a draft stream with `draft_tag` chunks but no `draft_topic` chunk must surface a `CoreException`, not a bare `AssertionError`.
- **Shrunk input** — `[ReplyTextChunk(text='handoff'), DraftTagChunk(label=Label(value='orphan-tag'))]`.
- **Replay** — deterministic chunk list above (no Hypothesis shrink needed).
- **Proposed pin** — `test_R3_F2_draft_tag_without_prior_topic_raises_core_exception` in `backend/tests/unit/capture/test_send_message_command.py`.
- **Evidence** — proof-test skipped: HEAD on default branch
- **Fix:** the orphan-tag stream must raise `CoreException` (not `AssertionError`) in the example suite until fixed, then remain as regression.

## Classified (not triaged)

- **Embedding equality via `==`** — `DeterministicEmbeddingAdapter` can produce `nan` components; Python float equality makes `topic.embedding == expected_emb` false even when both come from the same `embed()` call. Classified as property too strong / harness oracle issue, not a resolver defect.
- **Whitespace-only draft body** — `NoteContent(value=draft_text)` raises `EmptyNoteContentError` when accumulated draft text strips to empty; rollback leaves no artifacts. Treated as illegal input to the assembly step, not a specimen.
- **Empty agent reply text** — streams with draft chunks but no `ReplyTextChunk` raise `EmptyMessageContentError` before draft assembly; rollback holds. Illegal input.

## Retractions

(none)
