# Card-to-Anchor Jump Implementation Plan

## Overview

From a card, the user reaches its note with the source fragment distinguished from the rest of the content (AC-13 / FR-013). Anchor resolution moves out of the adapter parser and into the distill domain as a value object with a pluggable format strategy, so a single rule serves both the generation-time grounding check and the read-time jump. The backend resolves the fragment's position and hands the TUI a location it can render without knowing anything about markdown.

## Current State Analysis

Cards already carry a verbatim `anchor.quote` (`domain/distill/value_objects.py:86-102`), mandatory on every card (`domain/distill/card.py:15-22`). Grounding at generation time runs through the `NoteDocumentParser` application port (`application/distill/ports.py:13-14`), implemented once by `MarkdownNoteDocumentParser` (`adapters/out/in_memory/distill/note_document_parser.py`), which splits content on blank lines, normalizes each block (strip leading markers, drop inline emphasis characters, collapse whitespace) and answers a boolean.

The read surface exposes no position at all: `GET /notes/{note_id}` returns `content` as one string (`application/distill/queries/get_note.py:20-28`) and `GET /notes/{note_id}/cards` returns `anchor_quote` (`application/distill/queries/list_cards_for_note.py:10-15`). The TUI has the full browsing stack from S-04 and S-06 — tab strip, card list, card detail — but no jump gesture, no anchor state, and `NoteDetailScreen.tsx:47` renders the whole note as a single `<Text wrap="wrap">`.

### Key Discoveries:

- The parser's normalization discards positions (`note_document_parser.py:26-29` uses `re.sub` and `str.replace`), so exact-span highlighting requires a rewrite that carries an offset map, not a wrapper around today's code.
- `AnchorResolution` already exists in the domain (`domain/distill/value_objects.py:111-113`) and is what `CardFactory.mint` consumes (`domain/distill/card_factory.py:22-28`), so the factory needs no change — only the way the verdict is produced.
- The parser port has a contract suite parametrized over implementations (`tests/unit/distill/contracts/test_note_document_parser_contract.py:11-12`), which `foundation/rules/contract-testing.md` mandates per port; deleting the port legitimately retires that suite in favour of domain unit tests.
- Five test surfaces reach the parser and must migrate with it: `test_generate_cards_command.py:44-51`, `test_flashcard_gen_handler.py:39-43`, `test_card_generation_contract.py:20-34`, `tests/integration/support/in_memory_distill.py:38-75`, and the grounding step at `tests/bdd/steps/distill.py:114-127`.
- HTTP integration tests assert field-by-field, never whole-body equality (`tests/integration/test_notes_http.py:95-101,132-134`), so additive DTO fields do not break them.
- `useAppStore`'s `clearedNoteView` (`tui/src/store/index.ts:24-27`) is the existing seam for per-note view state — highlight state belongs in it, cleared on the same four transitions.
- ADR `distill-domain-shape` alternative 12 rejected fixing the matching rule as domain behaviour, calling it adapter business. This change reverses that, with the user's decision recorded on the change's `adr_refs`.

## Desired End State

`GET /notes/{note_id}` returns the note's content additionally as ordered `blocks`, and `GET /notes/{note_id}/cards` returns each live card's `anchor_location` — block index, character bounds within that block, and a precision of `exact` or `block` — or `null` when the quote no longer resolves. In the TUI, `Enter` on a card's detail switches to the note tab with the note rendered from the anchored block downward and the fragment visually marked; an unresolved anchor opens the note from the top with a visible notice.

Verify by generating cards for a note, opening a card, pressing `Enter`, and seeing the quoted passage marked in place; and by `curl`ing both endpoints to see `blocks` and a populated `anchor_location`.

## What We're NOT Doing

- General scrolling of note content. The anchored viewport renders from the highlighted block downward; the scroll model deferred by S-04 stays deferred.
- Persisting anchor positions. Resolution stays at read time, per ADR `distill-domain-shape` — no offsets or block indices are stored on a card.
- A jump gesture from the card list row. `Enter` there keeps its meaning (open the card).
- Any rich-text or non-markdown `NoteFormat` implementation. The strategy seam exists; only `MarkdownNoteFormat` is written.
- Editing notes, regenerating cards, removing cards, or the FR-014 readiness notification — effort non-goals, unchanged here.
- Highlighting a quote that spans two blocks. Single-block resolution stays the rule; a multi-block quote is unresolved.

## Implementation Approach

The mechanism becomes two domain types and no port. `NoteFormat` is a domain-level strategy protocol answering two questions about a serialization format — how content splits into blocks, and how a block's raw text normalizes into comparable text *plus an offset map back to the raw characters*. `MarkdownNoteFormat` is its only implementation and inherits the four patterns from the deleted adapter. `NoteDocument` holds the blocks and the format that produced them, and `locate(anchor)` expresses the rule itself: normalize the quote, find the first block whose normalized text contains it, map the match back through the offset map, and return an `AnchorLocation`. Because the rule never touches a regex, a fake format in the tests proves it is format-agnostic.

`GenerateCards` then builds a `NoteDocument` once per note and derives `AnchorResolution` from whether `locate` returned anything — the parser port, its adapter, and its injection disappear from `compose.py`. The two query adapters build the same document to fill `blocks` and per-card `anchor_location`. Nothing new enters the composition root: a strategy with a default is not a port.

The TUI stops rendering `content` as one string and renders `blocks`, slicing `block.text[start:end]` for the highlight. It never learns a normalization rule.

## Critical Implementation Details

`normalize` must produce the offset map by walking the raw text character by character and recording each surviving character's source index — today's `re.sub`/`replace` chain cannot be adapted, because both discard positions. Precision then falls out of one check: re-normalize the recovered raw span, and if it equals the normalized quote the span is `exact`; otherwise the recovery swept in real text and the location degrades to the whole block (`start=0`, `end=len(block.text)`). Phases 4 and 6 both depend on a running backend — the OpenAPI regeneration in phase 6 reads `localhost:8000/openapi.json`.

## Phase 1: Domain anchor-location contracts

### Overview

Materialize the symbols phase 2's tests will import: the format strategy and the document/location types, with unimplemented bodies.

### Changes Required:

#### 1. Note format strategy

**File**: `backend/src/domain/distill/note_format.py`

**Intent**: Give the domain a seam for "what counts as formatting noise", so a later rich-text format is a new class in the same package rather than a change to the matching rule.

**Contract**: Exports `NormalizedText(BaseModel, frozen=True)` with `value: str` and `offsets: tuple[int, ...]`; a `NoteFormat(Protocol)` with `blocks(self, content: str) -> list[str]` and `normalize(self, text: str) -> NormalizedText`; a `MarkdownNoteFormat` class implementing both with `raise NotImplementedError` bodies; and a module-level `MARKDOWN = MarkdownNoteFormat()`. `offsets[i]` is the index in the raw text of the i-th character of `value`, so `len(offsets) == len(value)`.

#### 2. Note document and anchor location

**File**: `backend/src/domain/distill/note_document.py`

**Intent**: Materialize the value objects that carry the note's block structure and a resolved anchor's position.

**Contract**: Exports `AnchorPrecision(StrEnum)` with `EXACT = "exact"` and `BLOCK = "block"`; `NoteBlock(BaseModel, frozen=True)` with `index: int` and `text: str` (raw); `AnchorLocation(BaseModel, frozen=True)` with `block_index: int`, `start: int`, `end: int`, `precision: AnchorPrecision`, where `start`/`end` are bounds within `NoteBlock.text`, not the whole note; and `NoteDocument(BaseModel, frozen=True)` with `blocks: list[NoteBlock]`, `note_format: NoteFormat`, a classmethod `of(cls, content: NoteContent, note_format: NoteFormat = MARKDOWN) -> "NoteDocument"`, and `locate(self, anchor: Anchor) -> AnchorLocation | None`. Both bodies `raise NotImplementedError`.

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run pytest` passes (new modules are unreferenced; nothing regresses)
- `cd backend && uv run ruff check src` and `cd backend && uv run basedpyright` pass

---

## Phase 2: Domain anchor-location behavior

### Overview

Implement the markdown strategy with its offset map and the matching rule that turns a quote into an `AnchorLocation`, with the two-tier precision and the unresolved case.

### Changes Required:

#### 1. Markdown format implementation

**File**: `backend/src/domain/distill/note_format.py`

**Intent**: Carry over the deleted adapter's four rules and add the position tracking that exact-span highlighting needs.

**Contract**: `blocks` splits on `\n\s*\n` and drops blank blocks. `normalize` strips a leading `^(?:[#>+-]+|\d+[.)])\s*`, drops `*`, `_` and backtick, collapses whitespace runs to one space, trims the ends — and records, for every character it keeps, the index it came from in the raw text. Module-private constants and helpers sit below the public class per `context/foundation/rules/code-ordering.md`.

```python
def normalize(self, text: str) -> NormalizedText:
    # walk char by char; re.sub/replace cannot be reused — both discard positions
    kept: list[str] = []
    offsets: list[int] = []
    ...
    return NormalizedText(value="".join(kept), offsets=tuple(offsets))
```

#### 2. Anchor location rule

**File**: `backend/src/domain/distill/note_document.py`

**Intent**: Express the matching rule itself, independent of any format's syntax.

**Contract**: `of` builds one `NoteBlock` per `note_format.blocks(content.value)` entry, indexed from zero, and keeps the format on the document. `locate` normalizes `anchor.quote`, returns `None` on an empty result, scans blocks in order and takes the first whose normalized `value` contains the normalized quote. Raw bounds come from the offset map: `start = offsets[i]`, `end = offsets[i + len(quote) - 1] + 1`. Precision is `EXACT` when re-normalizing `block.text[start:end]` yields the normalized quote, otherwise the location degrades to `start=0`, `end=len(block.text)`, `precision=BLOCK`. No match in any block returns `None`.

#### 3. Tests

**File**: `backend/tests/unit/distill/test_note_format.py`, `backend/tests/unit/distill/test_note_document.py`

**Intent**: Pin the rule and the offset map, including the cases the retired parser contract suite covered.

**Contract**: Format tests cover block splitting, marker stripping, emphasis removal, whitespace collapse, and that `offsets` indexes back to the right raw characters. Document tests cover: a plain-paragraph quote resolving `EXACT` with `block.text[start:end]` equal to the quote; a quote whose raw form carries emphasis resolving `EXACT` with the span covering the markup; a heading-derived match degrading to `BLOCK`; a match in the second block reporting `block_index == 1`; an absent quote and a whitespace-only quote both returning `None`; and a fake `NoteFormat` proving `locate` is format-agnostic.

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run pytest tests/unit/distill -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run ruff check src tests` and `cd backend && uv run basedpyright` pass

#### Manual Verification:

- `cd backend && uv run python -c "from domain.distill.note_document import NoteDocument; from domain.distill.value_objects import Anchor, NoteContent; print(NoteDocument.of(NoteContent(value='# TCP\n\nThe **handshake** begins here.')).locate(Anchor(quote='handshake begins here')))"` prints a location with `block_index=1` and `precision` reported

### Review r1

Artifact: `reviews/2026-09-08-r1-property-test-phase-2.md`

- `R1-F1` — Leading emphasis at block start marks the whole paragraph
  Fix: The shrunk input (`lead in\n\n**aaa** and aaaaaaaaaaaaaaaa` / quote `aaa`) must fail the example suite until locate is `exact` and the raw slice does not contain `aaaaaaaaaaaaaaaa`, then remain as regression

### Review r2

Artifact: `reviews/2026-09-08-r2-mutation-test-phase-2.md`

- `R2-F1` — Multi-character and numbered leading markers are not stripped
  Fix: Normalizing a block drops exactly one leading run matching `^(?:[#>+-]+|\d+[.)])\s*` (including `## Title`, `> quote`, `- item`, and `1. item`) and keeps the remainder as comparable text.
- `R2-F2` — Block split strips indentation not just newlines
  Fix: After splitting on blank lines, a kept block retains leading and trailing spaces; only surrounding newlines are stripped.
- `R2-F3` — Normalize does not pin trimming of leading and trailing whitespace
  Fix: `normalize` omits leading and trailing whitespace from `value` and from `offsets`; a quote padded with spaces still matches the unpadded block.
- `R2-F4` — Locate takes the last in-block match
  Fix: When the normalized quote occurs more than once in a block, `locate` marks the first span, not the last.
- `R2-F5` — Exact end bound can extend one raw character past the quote
  Fix: An `exact` location's `end` is exclusive of the raw character after the last kept quote character (`offsets[last] + 1`), so a following letter is not swept into the span and must not force `block` precision.

---

## Phase 3: Generation on the domain locator

### Overview

Retire the `NoteDocumentParser` port, its adapter, and its injection; `GenerateCards` asks the domain instead. Behaviour is unchanged and the existing suites are the oracle.

### Changes Required:

#### 1. Port removal

**File**: `backend/src/application/distill/ports.py`, `backend/src/adapters/out/in_memory/distill/note_document_parser.py`

**Intent**: Remove the seam the domain now owns.

**Contract**: The `NoteDocumentParser` protocol is deleted; `CardGeneration` and `UnitOfWork` are untouched. `note_document_parser.py` is deleted outright.

#### 2. Generation command

**File**: `backend/src/application/distill/commands/generate_cards.py`

**Intent**: Derive the grounding verdict from the domain rather than an injected collaborator.

**Contract**: `__init__` loses its `parser` parameter, keeping `(uow_factory, card_generation, card_factory)`. `handle` builds `NoteDocument.of(note.content)` once, before the proposal loop, and per proposal sets `resolution = AnchorResolution.RESOLVED if document.locate(anchor) is not None else AnchorResolution.UNRESOLVED`. The `await` on the resolution call disappears — `locate` is synchronous. `CardFactory.mint` is called unchanged.

#### 3. Composition

**File**: `backend/src/adapters/compose.py`

**Intent**: Stop constructing and injecting a collaborator that no longer exists.

**Contract**: Drop the `MarkdownNoteDocumentParser` import, the `_note_document_parser` instance, and the `parser=` keyword on the `GenerateCardsCommand` construction. Nothing is added — a strategy with a default is not a port.

#### 4. Test migration

**File**: `backend/tests/unit/distill/contracts/test_note_document_parser_contract.py`, `backend/tests/unit/distill/test_generate_cards_command.py`, `backend/tests/unit/distill/test_flashcard_gen_handler.py`, `backend/tests/unit/distill/contracts/test_card_generation_contract.py`, `backend/tests/integration/support/in_memory_distill.py`, `backend/tests/bdd/steps/distill.py`

**Intent**: Move every parser-shaped test surface onto the domain type without changing what any of them assert.

**Contract**: The parser contract suite is deleted (its cases live in phase 2's document tests). `_StubNoteDocumentParser` disappears from both command tests, which construct the command without a parser and choose note content whose blocks do or do not contain the fixture quotes. `test_card_generation_contract.py`'s `_resolves` helper becomes `NoteDocument.of(content).locate(Anchor(quote=proposal.quote)) is not None`. `InMemoryDistillComposition` drops its `note_document_parser` field and the `parser=` argument. The `every live card's quote resolves within the held note` step resolves through `NoteDocument` instead of the composition's parser.

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run pytest` passes with no test skipped or removed beyond the retired contract suite
- `cd backend && uv run pytest tests/bdd -v` passes
- `cd backend && grep -rn "NoteDocumentParser\|note_document_parser" src tests` returns nothing
- `cd backend && uv run ruff check src tests` and `cd backend && uv run basedpyright` pass

#### Manual Verification:

- `cd backend && uv run fastapi dev src/main.py`, approve a note through the capture flow, and confirm cards are still generated and grounded (a note whose quote is absent still yields no live card)

---

## Phase 4: Read-model anchor contracts

### Overview

Materialize the DTO fields the read path will fill, wired to empty values so the existing suites stay green.

### Changes Required:

#### 1. Note detail blocks

**File**: `backend/src/application/distill/queries/get_note.py`

**Intent**: Give the note read surface the block structure the TUI needs to render and anchor on.

**Contract**: Adds `NoteBlockDTO(BaseModel)` with `index: int` and `text: str`, and `blocks: list[NoteBlockDTO]` on `NoteDetailDTO`. `content: str` stays — it is the existing contract and blocks are derived from it deterministically. `GetNoteQueryPort`'s signature is unchanged.

#### 2. Card anchor location

**File**: `backend/src/application/distill/queries/list_cards_for_note.py`

**Intent**: Give each card a resolved position alongside the quote it already carries.

**Contract**: Adds `AnchorLocationDTO(BaseModel)` with `block_index: int`, `start: int`, `end: int`, `precision: str` (`"exact"` or `"block"`), and `anchor_location: AnchorLocationDTO | None` on `CardListItemDTO`. `anchor_quote` stays. `ListCardsForNoteQueryPort`'s signature is unchanged.

#### 3. Query adapter shells

**File**: `backend/src/adapters/out/in_memory/distill/get_note_query.py`, `backend/src/adapters/out/in_memory/distill/list_cards_for_note_query.py`

**Intent**: Satisfy the new required fields without resolving anything yet.

**Contract**: `get_note` passes `blocks=[]`; `list_cards_for_note` passes `anchor_location=None` for every card. No `NoteDocument` import yet.

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run pytest` passes (integration assertions are field-wise, so additive fields do not break them)
- `cd backend && uv run ruff check src` and `cd backend && uv run basedpyright` pass

#### Manual Verification:

- `cd backend && uv run fastapi dev src/main.py`, then `curl -s localhost:8000/openapi.json | grep -o 'anchor_location\|NoteBlockDTO'` shows both new shapes registered

---

## Phase 5: Read-model behavior and US-07 acceptance

### Overview

Fill `blocks` and per-card `anchor_location` from the domain, and give AC-13 acceptance coverage where the logic now lives.

### Changes Required:

#### 1. Note detail blocks

**File**: `backend/src/adapters/out/in_memory/distill/get_note_query.py`

**Intent**: Serve the note's block structure from the same rule that resolves anchors.

**Contract**: Builds `NoteDocument.of(note.content)` and maps each `NoteBlock` to a `NoteBlockDTO`, preserving order and index. `content` still carries the raw note.

#### 2. Card anchor resolution

**File**: `backend/src/adapters/out/in_memory/distill/list_cards_for_note_query.py`

**Intent**: Resolve every live card's anchor once per request.

**Contract**: Builds `NoteDocument.of(note.content)` once, before mapping, and calls `locate(card.anchor)` per live card; `None` maps to `anchor_location=None`, a location maps field-for-field with `precision` serialized as its enum value. Live-card filtering and `created_at` ordering are unchanged.

#### 3. HTTP coverage

**File**: `backend/tests/integration/test_notes_http.py`

**Intent**: Pin the wire shape both endpoints now produce.

**Contract**: Note detail returns `blocks` in document order with the raw block text; the cards route returns an `exact` location whose bounds slice the quote out of the addressed block, a `block` location for a formatting-drifted quote, and `null` for a card whose quote no longer resolves.

#### 4. US-07 acceptance

**File**: `backend/tests/features/distill-flow/US-07-card-anchor-jump.feature`, `backend/tests/bdd/steps/anchor_jump.py`, `backend/tests/bdd/test_features.py`

**Intent**: Cover AC-13's backend half — that a card reaches the passage it came from — in the effort's acceptance suite.

**Contract**: Scenarios tagged `distill-flow` and `AC-13`: a live card's anchor resolves to a location within the held note; a card whose quote survives only normalization resolves at block precision; a card whose quote no longer resolves reports no location and the note stays readable. Step definitions go in a new `anchor_jump` module registered in `test_features.py`'s `pytest_plugins`.

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run pytest tests/integration/test_notes_http.py -v` passes
- `cd backend && uv run pytest tests/bdd -m "distill-flow and AC-13" -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run ruff check src tests` and `cd backend && uv run basedpyright` pass

#### Manual Verification:

- `cd backend && uv run fastapi dev src/main.py`, then `curl -s localhost:8000/notes/<note_id>/cards | jq '.[0].anchor_location'` and `curl -s localhost:8000/notes/<note_id> | jq '.blocks[0]'` for a generated note show a populated location and the note's blocks

---

## Phase 6: TUI anchor surface stubs

### Overview

Regenerate the API types and materialize the client-side symbols the jump behaviour will use, leaving today's rendering intact.

### Changes Required:

#### 1. Regenerated OpenAPI types

**File**: `tui/src/api/generated/schema.d.ts`

**Intent**: Pick up `blocks` and `anchor_location` from the running backend.

**Contract**: Regenerated by `pnpm generate:api` against `localhost:8000/openapi.json`; hand edits are never made to this file.

#### 2. Note and card API types

**File**: `tui/src/api/notes.ts`, `tui/src/api/cards.ts`

**Intent**: Carry the new fields through the client mapping layer.

**Contract**: `notes.ts` exports `NoteBlock = { index: number; text: string }` and adds `blocks: NoteBlock[]` to `NoteDetail`, mapped from `data.blocks`. `cards.ts` exports `AnchorLocation = { blockIndex: number; start: number; end: number; precision: "exact" | "block" }` and adds `anchorLocation: AnchorLocation | null` to `Card`, mapped from `item.anchor_location`. `content` and `anchorQuote` are unchanged.

#### 3. Highlight state

**File**: `tui/src/store/index.ts`

**Intent**: Materialize the store shape the jump gesture writes and the note screen reads.

**Contract**: Adds `highlightedAnchor: { cardId: string; location: AnchorLocation | null } | null` to `AppState`, initialized `null` inside `clearedNoteView`, and a `jumpToAnchor: (cardId: string, location: AnchorLocation | null) => void` action to `AppActions`. Clearing semantics and the tab switch land in phase 7.

### Success Criteria:

#### Automated Verification:

- `cd tui && pnpm typecheck`, `cd tui && pnpm lint`, `cd tui && pnpm build` pass
- `cd tui && pnpm test` passes (existing suites unaffected)

#### Manual Verification:

- `cd tui && grep -c 'anchor_location' src/api/generated/schema.d.ts` returns a non-zero count, confirming the regenerated schema carries the new field

---

## Phase 7: Jump gesture and anchored highlight

### Overview

`Enter` on a card's detail lands the user in the note tab with the fragment marked and the content rendered from that block downward; an unresolved anchor degrades loudly.

### Changes Required:

#### 1. Jump action

**File**: `tui/src/store/index.ts`

**Intent**: Make the jump one atomic state transition, so no intermediate render shows the wrong tab.

**Contract**: `jumpToAnchor(cardId, location)` sets `activeNoteTab: "note"`, `selectedCardId: null`, and `highlightedAnchor: { cardId, location }` in a single `set`. `setActiveNoteTab`, `openDetail`, `closeDetail` and `closeNotes` all clear `highlightedAnchor` — the first explicitly, the other three through `clearedNoteView`.

#### 2. Card detail gesture

**File**: `tui/src/screens/CardDetailScreen.tsx`

**Intent**: Give the card a way back to its source passage without disturbing the existing back gesture.

**Contract**: `useInput` handles `key.return` by calling `jumpToAnchor(card.cardId, card.anchorLocation)`; `key.leftArrow` keeps closing the card. A hint line names both keys. No jump fires when no card is resolved.

#### 3. Anchored note rendering

**File**: `tui/src/screens/NoteDetailScreen.tsx`

**Intent**: Render the note from blocks so the source fragment can be marked and guaranteed visible.

**Contract**: Renders `note.blocks` instead of `note.content`. With no `highlightedAnchor`, all blocks render from the top, unchanged in appearance. With a location, rendering starts at `location.blockIndex` and that block splits into three runs — `text.slice(0, start)`, `text.slice(start, end)` marked with `inverse`, `text.slice(end)` — which for `precision: "block"` marks the block whole. With `highlightedAnchor` whose `location` is `null`, blocks render from the top under a visible notice that the source fragment was not found in this note.

#### 4. Tests

**File**: `tui/test/cardDetailScreen.test.tsx`, `tui/test/noteDetailScreen.test.tsx`, `tui/test/appStore.test.ts`

**Intent**: Cover the gesture, the three render modes, and the highlight's lifecycle.

**Contract**: Card detail: `Enter` switches the active tab to `note`, clears the selected card, and stores the card's location. Note detail: an `exact` location marks exactly the quoted run; a `block` location marks the whole block; rendering starts at the anchored block, so content above it is absent; a `null` location renders from the top with the notice. Store: `jumpToAnchor` writes all three fields at once, and each of the four clearing transitions drops the highlight.

### Success Criteria:

#### Automated Verification:

- `cd tui && pnpm test` passes
- `cd tui && pnpm typecheck`, `cd tui && pnpm lint`, `cd tui && pnpm build` pass
- `cd backend && uv run pytest` passes

#### Manual Verification:

- Start `cd backend && uv run fastapi dev src/main.py` and `cd tui && pnpm start`; open a note with cards, enter the cards tab, open a card, press `Enter`, and confirm the note tab opens with the passage marked and visible at the top of the viewport
- Repeat on a note whose first block is a heading, confirming the block-precision path marks the whole block rather than a wrong slice

---

## Testing Strategy

### Unit Tests:

`test_note_format.py` pins block splitting, normalization and the offset map. `test_note_document.py` pins the matching rule end to end, including both precisions, the unresolved cases, and format-agnosticism via a fake `NoteFormat`. The retired `test_note_document_parser_contract.py` cases are carried into the latter.

### Integration Tests:

`test_notes_http.py` pins the wire shape of `blocks` and `anchor_location` across exact, degraded and unresolved cards. `backend/tests/features/distill-flow/US-07-card-anchor-jump.feature` covers AC-13 at the acceptance level.

### Manual Testing Steps:

Approve a note through capture, wait for cards, open a card, press `Enter`, and confirm the marked passage. Repeat on a heading-anchored card for the block-precision path.

## Performance Considerations

`NoteDocument.of` runs once per request in each query adapter, not once per card, and `locate` is a linear scan over blocks with a per-block normalization. Note content is bounded at 20 000 characters (`NOTE_CONTENT_MAX_LENGTH`), so the whole resolution is bounded well below any request budget. Generation drops an `await` per proposal by moving from an async port to a synchronous domain call.

## Migration Notes

No data migration: nothing is persisted by this change. The `NoteDocumentParser` port and its adapter are deleted in phase 3 along with the port's contract suite — `foundation/rules/contract-testing.md` requires one suite per port, and there is no longer a port. `NoteDetailDTO` carries both `content` and `blocks`; the redundancy is deliberate, keeps the existing contract intact, and cannot diverge because blocks are derived from content on every read.

## References

- `context/changes/distill-flow-card-anchor-jump/research.md` — scope research for this slice
- `context/efforts/distill-flow/stories.md:66-72` — US-07 and AC-13
- `context/efforts/distill-flow/prd.md:58` — FR-013
- `context/adrs/distill-domain-shape/decision.md` — quote-at-read-time; alternative 12 placed the matching rule in an adapter, which this change reverses
- `context/foundation/rules/layering.md`, `cqrs-lite.md`, `contract-testing.md`, `code-ordering.md`
- Execution state for this plan lives in `todos.md`, sibling of this file.
