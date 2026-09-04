---
change_id: distill-flow-grounded-generation
current_phase: 1
next_step: 1.4
next_command: /implement distill-flow-grounded-generation phase 1
updated: 2026-09-04
---

### Phase 1: Card value objects and exceptions — stubs

#### Automated

- [x] 1.1 Add `EmptyCardSideError`, `CardSideTooLongError`, `EmptyAnchorError`, `IdenticalCardSidesError`, `InvalidDistillationTransitionError` — `domain/distill/exceptions.py`
- [x] 1.2 Add `CardId`, `CardSide`, `Anchor`, `DiscardReason`, `AnchorResolution`, `Discard`, `CardLengthPolicy` (fields and constants only) — `domain/distill/value_objects.py`
- [x] 1.3 `cd backend && uv run ruff check src` and `uv run basedpyright` clean, every new symbol importable

#### Manual

- [ ] 1.4 Import every new card symbol in a one-liner and confirm it resolves

### Phase 2: Card value objects and exceptions — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Implement `CardSide` and `Anchor` strip, non-empty and absolute-bound validation — `domain/distill/value_objects.py`
- [ ] 2.2 Implement `CardLengthPolicy.breach` with front-then-back ordering and the side-naming detail string — `domain/distill/value_objects.py`
- [ ] 2.3 Write the card value-object and policy tests — `tests/unit/distill/test_card_value_objects.py`
- [ ] 2.4 `cd backend && uv run pytest` green and `uv run ruff check src tests` clean

#### Manual

- [ ] 2.5 Read `uv run pytest tests/unit/distill -v` names as a statement of the card-side rules

### Phase 3: Card aggregate and CardFactory — stubs

#### Automated

- [ ] 3.1 Add `Card` with its fields and an unimplemented `_validate_sides_differ` — `domain/distill/card.py`
- [ ] 3.2 Add `CardFactory` with an unimplemented `mint` taking an `AnchorResolution` — `domain/distill/card_factory.py`
- [ ] 3.3 `cd backend && uv run ruff check src` and `uv run basedpyright` clean, both symbols importable

#### Manual

- [ ] 3.4 Print `CardFactory.mint.__annotations__` and confirm the signature

### Phase 4: Card aggregate and CardFactory — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Implement the differing-sides invariant with casefold canonicalization — `domain/distill/card.py`
- [ ] 4.2 Implement `mint`'s fixed order: construct, grounding, length policy, first violation wins — `domain/distill/card_factory.py`
- [ ] 4.3 Write the aggregate and factory tests — `tests/unit/distill/test_card.py`, `tests/unit/distill/test_card_factory.py`
- [ ] 4.4 `cd backend && uv run pytest` green

#### Manual

- [ ] 4.5 Confirm the ordering test name states grounding-before-length

### Phase 5: Note transitions and repository ports — stubs

#### Automated

- [ ] 5.1 Add `mark_ready`, `mark_failed` and `_ensure_generating` with unimplemented bodies — `domain/distill/note.py`
- [ ] 5.2 Rename `NoteRepository.add` to `save` and add `CardRepository` with `save` / `list_by_note` — `domain/distill/ports.py`
- [ ] 5.3 Carry the rename to the adapter and the one call site — `adapters/out/in_memory/distill/note_repository.py`, `application/distill/commands/save_note.py`
- [ ] 5.4 Add the `InMemoryCardRepository` skeleton with `save`, `list_by_note`, `snapshot`, `restore` — `adapters/out/in_memory/distill/card_repository.py`
- [ ] 5.5 `cd backend && uv run ruff check src` and `uv run basedpyright` clean, `tests/unit/distill/test_save_note_command.py` still green

#### Manual

- [ ] 5.6 Grep `src` for `notes.add` and confirm no call site remains

### Phase 6: Note transitions and repository ports — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Implement `_ensure_generating` raising `InvalidDistillationTransitionError` and both transitions — `domain/distill/note.py`
- [ ] 6.2 Implement `InMemoryCardRepository`'s `save`, `list_by_note`, `snapshot`, `restore` — `adapters/out/in_memory/distill/card_repository.py`
- [ ] 6.3 Rename the note contract suite's three cases to `save` — `tests/unit/distill/contracts/test_note_repository_contract.py`
- [ ] 6.4 Write the card repository contract suite incl. discarded rows appearing in `list_by_note` — `tests/unit/distill/contracts/test_card_repository_contract.py`
- [ ] 6.5 Write the transition tests incl. both illegal-transition cases — `tests/unit/distill/test_note.py`
- [ ] 6.6 `cd backend && uv run pytest` green

#### Manual

- [ ] 6.7 Confirm both contract suites report the `in_memory` parametrization id

### Phase 7: Application ports and outbound adapters — stubs

#### Automated

- [ ] 7.1 Add `CardProposal` carrying raw `front` / `back` / `quote` — `application/distill/value_objects.py`
- [ ] 7.2 Add the `CardGeneration` and `NoteDocumentParser` ports and `UnitOfWork.cards` — `application/distill/ports.py`
- [ ] 7.3 Bring the card repository under snapshot and restore — `adapters/out/in_memory/distill/unit_of_work.py`
- [ ] 7.4 Add the parser and generation adapter skeletons — `adapters/out/in_memory/distill/note_document_parser.py`, `adapters/out/in_memory/distill/card_generation.py`
- [ ] 7.5 `cd backend && uv run ruff check src` and `uv run basedpyright` clean, `uv run pytest` green

#### Manual

- [ ] 7.6 Import both ports and the extended `UnitOfWork` in a one-liner

### Phase 8: NoteDocumentParser — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Implement block splitting and the shared normalization — collapse whitespace, strip inline emphasis and block markers — `adapters/out/in_memory/distill/note_document_parser.py`
- [ ] 8.2 Implement single-block substring resolution incl. the empty-quote-never-resolves rule — `adapters/out/in_memory/distill/note_document_parser.py`
- [ ] 8.3 Write the parser contract suite — `tests/unit/distill/contracts/test_note_document_parser_contract.py`
- [ ] 8.4 `cd backend && uv run pytest` green

#### Manual

- [ ] 8.5 Read the parser contract case names as the statement of the matching rule

### Phase 9: Deterministic CardGeneration adapter — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Implement block-derived proposals, skipping any block whose remainder is empty — `adapters/out/in_memory/distill/card_generation.py`
- [ ] 9.2 Append the one fabricated proposal with its sentinel quote — `adapters/out/in_memory/distill/card_generation.py`
- [ ] 9.3 Write the generation contract suite incl. determinism and the single unresolvable proposal — `tests/unit/distill/contracts/test_card_generation_contract.py`
- [ ] 9.4 `cd backend && uv run pytest` green

#### Manual

- [ ] 9.5 Run the adapter on a two-block note in a one-liner and read the proposals

### Phase 10: Command and handler — stubs

#### Automated

- [ ] 10.1 Add `GenerateCardsCommand` with a uow factory and an unimplemented `handle` — `application/distill/commands/generate_cards.py`
- [ ] 10.2 Add `FlashcardGenHandler` with `envelope_type = NOTE_SAVED` and an unimplemented `handle` — `adapters/out/worker/handlers/flashcard_gen.py`
- [ ] 10.3 `cd backend && uv run ruff check src` and `uv run basedpyright` clean

#### Manual

- [ ] 10.4 Print `FlashcardGenHandler.envelope_type` and confirm it is `note_saved`

### Phase 11: GenerateCardsCommand — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 11.1 Implement the load plus the missing-note and non-`generating` logged no-ops — `application/distill/commands/generate_cards.py`
- [ ] 11.2 Implement the generation-failure path through `mark_failed` — `application/distill/commands/generate_cards.py`
- [ ] 11.3 Implement the per-proposal resolve, mint and save loop with the `CoreException` catch-and-continue — `application/distill/commands/generate_cards.py`
- [ ] 11.4 Implement `mark_ready` regardless of live card count, then save and commit — `application/distill/commands/generate_cards.py`
- [ ] 11.5 Write the command tests incl. zero-live-cards, generation failure, redelivery no-op and rollback — `tests/unit/distill/test_generate_cards_command.py`
- [ ] 11.6 `cd backend && uv run pytest` green

#### Manual

- [ ] 11.7 Confirm the zero-live-cards case is named as a success, not a failure

### Phase 12: FlashcardGenHandler — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 12.1 Implement validate-via-`NoteSavedPayload` and delegate to the command — `adapters/out/worker/handlers/flashcard_gen.py`
- [ ] 12.2 Implement the malformed-payload path: log and return without raising — `adapters/out/worker/handlers/flashcard_gen.py`
- [ ] 12.3 Write the handler tests incl. the malformed-payload case — `tests/unit/distill/test_flashcard_gen_handler.py`
- [ ] 12.4 `cd backend && uv run pytest` green

#### Manual

- [ ] 12.5 `cd backend && uv run pytest tests/unit/distill -v`

### Phase 13: Composition

#### Automated

- [ ] 13.1 Add `card_front_max` and `card_back_max` — `config/settings.py`
- [ ] 13.2 Wire the card repository, parser, generation adapter, `CardFactory` and the extended distill unit of work — `adapters/compose.py`
- [ ] 13.3 Register `FlashcardGenHandler` after `SaveNoteHandler` in the `OutboxWorker` handler list — `adapters/compose.py`
- [ ] 13.4 Add the five new codes to `EXCEPTION_STATUS_MAP` — `adapters/http/errors.py`
- [ ] 13.5 `cd backend && uv run pytest` green incl. the exhaustiveness test, `uv run ruff check src` and `uv run basedpyright` clean

#### Manual

- [ ] 13.6 Approve a note through the running backend and confirm via `/_outbox` that `note_approved` and `note_saved` both reach `consumed`

### Phase 14: Acceptance scenarios for US-02 and US-03

#### Tests

- [ ] tests generated

#### Automated

- [ ] 14.1 Register the `distill-flow` marker — `pyproject.toml`
- [ ] 14.2 Add `InMemoryDistillComposition` over capture's shared outbox store, with a `worker()` builder — `tests/integration/support/in_memory_distill.py`
- [ ] 14.3 Add the `distill_composition` fixture depending on `capture_composition` — `tests/bdd/conftest.py`
- [ ] 14.4 Write the US-02 and US-03 feature files tagged `@distill-flow` plus AC ids — `tests/features/distill-flow/`
- [ ] 14.5 Write the drain, seed-a-held-note and assertion steps — `tests/bdd/steps/distill.py`
- [ ] 14.6 Register the step module in `pytest_plugins` — `tests/bdd/test_features.py`
- [ ] 14.7 `cd backend && uv run pytest tests/bdd -m "distill-flow" -v` green with four scenarios and `uv run pytest` green

#### Manual

- [ ] 14.8 `cd backend && uv run pytest tests/bdd -m "distill-flow and AC-04" -v` and confirm the zero-card scenario passes as a completed distillation
