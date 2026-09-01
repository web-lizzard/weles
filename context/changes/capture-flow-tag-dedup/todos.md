---
change_id: capture-flow-tag-dedup
current_phase: 2
next_step: 2.1
next_command: /unit-test capture-flow-tag-dedup phase 2
updated: 2026-09-01
---

### Phase 1: Domain vocabulary matching — stubs

#### Automated

- [x] 1.1 Add `SimilarityScore` and the `Embedding.cosine_similarity` signature — `domain/capture/value_objects.py`
- [x] 1.2 Add `SimilarityScoreOutOfRangeError`, `EmbeddingDimensionMismatchError`, `ZeroMagnitudeEmbeddingError` — `domain/capture/exceptions.py`
- [x] 1.3 Add `VocabularyEntryT`, `VocabularyMatch` and `MatchCriteria` with `best_match` raising `NotImplementedError` — `domain/capture/vocabulary.py`
- [x] 1.4 `cd backend && uv run pytest`, `uv run ruff check src tests`, `uv run basedpyright` all clean

### Phase 2: Domain vocabulary matching — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Implement the `SimilarityScore` range and finiteness validator
- [ ] 2.2 Implement `Embedding.cosine_similarity`: max-abs scaling, dimension and zero-magnitude guards, clamp into `[-1.0, 1.0]`
- [ ] 2.3 Implement `MatchCriteria.best_match`: threshold filter, highest score, `created_at` tie-break
- [x] 2.4 Add the three new codes to `EXCEPTION_STATUS_MAP` — `adapters/http/errors.py`
- [ ] 2.5 Write unit tests: score validation, cosine over identical/orthogonal/opposed/overflowing vectors, both guards, the four `best_match` cases
- [ ] 2.6 `cd backend && uv run pytest`, `uv run ruff check src tests`, `uv run basedpyright` all clean

### Phase 3: Candidate retrieval and embedding conditioning — stubs

#### Automated

- [ ] 3.1 Add `candidates()` to `TopicRepository` and `TagRepository` — `domain/capture/ports.py`
- [ ] 3.2 Add `candidates()` raising `NotImplementedError` to both in-memory repositories
- [ ] 3.3 Raise `_EMBEDDING_DIMENSION` from 8 to 32 — `adapters/out/in_memory/capture/embedding.py`
- [ ] 3.4 `cd backend && uv run ruff check src tests`, `uv run basedpyright` clean

### Phase 4: Candidate retrieval and embedding conditioning — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Implement `candidates()` on both in-memory repositories
- [ ] 4.2 Replace the `struct.unpack` reinterpretation with byte scaling into `[-1.0, 1.0]` — `adapters/out/in_memory/capture/embedding.py`
- [ ] 4.3 Extend both repository contract suites with `candidates()` cases: empty store, every added row, overwrite
- [ ] 4.4 Extend the `EmbeddingPort` contract with a finiteness and range case
- [ ] 4.5 Add a rollback case asserting uncommitted rows are absent from `candidates()` — `tests/unit/capture/test_unit_of_work.py`
- [ ] 4.6 `cd backend && uv run pytest`, `uv run ruff check src tests`, `uv run basedpyright` all clean

### Phase 5: Reuse-or-mint, stream contract and configuration — stubs

#### Automated

- [ ] 5.1 Add `ResolvedTopic` and `ResolvedTag` — `application/capture/value_objects.py`
- [ ] 5.2 Take `MatchCriteria` in `VocabularyResolver.__init__` and retype both `resolve_*` returns
- [ ] 5.3 Add `reused: bool` to `DraftTopicEvent` and `DraftTagEvent` — `application/capture/dto.py`
- [ ] 5.4 Add `vocabulary_match_threshold: float = 0.85` — `config/settings.py`
- [ ] 5.5 `cd backend && uv run ruff check src tests`, `uv run basedpyright` clean

### Phase 6: Reuse-or-mint, stream contract and configuration — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Rewrite `resolve_topic`/`resolve_tag` into reuse-or-mint over `candidates()` and `MatchCriteria.best_match`
- [ ] 6.2 Unwrap `ResolvedTopic`/`ResolvedTag` and forward `reused` into the draft events — `application/capture/commands/send_message.py`
- [ ] 6.3 Build `MatchCriteria` from `Settings` in the composition root — `adapters/compose.py`
- [ ] 6.4 Pass an explicit `MatchCriteria` at both test composition sites
- [ ] 6.5 Write unit tests: resolver reuse/mint/flag/within-stream reuse, `Settings` default and override, draft-event `reused`
- [ ] 6.6 `cd backend && uv run pytest`, `uv run ruff check src tests`, `uv run basedpyright` all clean

#### Manual

- [ ] 6.7 Boot the backend and confirm the new module-level `Settings()` call in `compose.py` does not break startup
- [ ] 6.8 Confirm `VOCABULARY_MATCH_THRESHOLD=5` fails loudly at import instead of starting with a broken threshold

### Phase 7: HTTP integration and acceptance scenarios (AC-10, AC-11)

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Assert `reused` on `draft_topic`/`draft_tag` frames across two sessions — `tests/integration/test_capture_http.py`
- [ ] 7.2 Write `US-05-vocabulary-reuse.feature` with the `@AC-10` and `@AC-11` scenarios
- [ ] 7.3 Write `tests/bdd/steps/vocabulary_reuse.py` and register it in `pytest_plugins`
- [ ] 7.4 Add the `AC-10` and `AC-11` markers — `pyproject.toml`
- [ ] 7.5 `cd backend && uv run pytest tests/bdd -m "capture-flow" -v` and `uv run pytest` green

#### Manual

- [ ] 7.6 `cd backend && uv run pytest tests/bdd --collect-only` lists both new scenarios with no unmatched step

### Phase 8: TUI reused-tag surfacing — stubs

#### Automated

- [ ] 8.1 Add `reused` to the draft event types and their raw counterparts — `tui/src/api/stream.ts`
- [ ] 8.2 Widen the draft state's `tags` to `{ label, reused }[]` — `tui/src/store/chat.ts`
- [ ] 8.3 `cd tui && pnpm lint` clean

### Phase 9: TUI reused-tag surfacing — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Propagate `reused` through `parseStreamEvent`'s two draft branches
- [ ] 9.2 Append `{ label, reused }` on `draft_tag` and merge recorded flags on `draft_done` — `tui/src/store/chat.ts`
- [ ] 9.3 Render newly minted tags distinctly in `DraftTags` — `tui/src/screens/CaptureScreen.tsx`
- [ ] 9.4 Write tests: parsing the flag, survival across `draft_done`, the unseen-label default
- [ ] 9.5 `cd tui && pnpm test`, `pnpm typecheck`, `pnpm lint` all clean

#### Manual

- [ ] 9.6 Run backend and TUI, hold the same conversation in two sessions, confirm the second renders its tags as reused
