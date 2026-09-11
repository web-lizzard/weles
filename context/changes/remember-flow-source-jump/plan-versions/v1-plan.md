# Source Jump During Review Implementation Plan

## Overview

A card under review can be ambiguous. This change gives the reviewer a route from
the card to the note fragment it was drawn from, and defines what happens to that
route when the fragment can no longer be found. The route opens only after the
back has been revealed, presents the fragment marked inside surrounding note text,
expands to the whole note without leaving, and returns to the card by a single Esc.

The change also carries one correction the domain needs regardless: `Sitting`
currently counts *every* review event toward a card's showing limit and draw seed.
That is only correct while every event is a grading. It stops being correct the
moment a non-grading event exists — which this change introduces.

## Current State Analysis

**Anchors ship end-to-end in distill, and stop at the remember boundary.**
`Card.anchor` holds a verbatim `quote` (`backend/src/domain/distill/value_objects.py:86-102`),
and `NoteDocument.locate` resolves it to a block index plus offsets at read time,
never persisted (`backend/src/domain/distill/note_document.py:46-85`). The browse
path already renders that as a highlight (`tui/src/screens/NoteDetailScreen.tsx:23-42`).

`InMemoryReviewCatalog` is the one place in the entire adapter tree that reads two
bounded contexts, and it deliberately drops the anchor: `ReviewableCard` is
`id`/`front`/`back` only (`backend/src/domain/remember/ports.py:14-17`,
`backend/src/adapters/out/in_memory/remember/review_catalog.py:42-47`).

**Revealing the back is not a fact anywhere.** `RevealBackQuery` is documented
"Read-only; no UnitOfWork" (`backend/src/application/remember/queries/reveal_back.py:35`)
and `Sitting` is a frozen aggregate of `card_ids` plus snapshotted limits, saved
write-once (`backend/src/domain/remember/sitting.py:26-33`,
`backend/src/domain/remember/ports.py:26-29`). Nothing records that a user saw a back.

**`Sitting` counts events, not gradings.** `_showing_count` is
`sum(1 for event in events if event.card_id == card_id)`
(`backend/src/domain/remember/sitting.py:150-151`), feeding `_card_is_finished`
against `showing_limit` (`sitting.py:153-160`). `_draw_seed` mixes every sitting
event into the hash that picks the next card (`sitting.py:167-188`), while
`CurrentCardQuery` is documented as returning "the stable next draw"
(`backend/src/application/remember/queries/current_card.py:36`).

**The TUI has no scrolling.** A repo-wide search of `tui/src` for
`scroll|overflow|paginat|viewport|truncat` returns nothing. `App.tsx:29-31` reads
`stdout.rows`/`columns` only to size fixed overlay boxes; content past the terminal
height is simply not visible.

**Esc already has one nesting level.** `SittingOverlay` intercepts Esc for the
reject-confirm prompt before closing the sitting (`tui/src/screens/SittingOverlay.tsx:49-57`),
and `App.tsx:35-54` applies the same innermost-first precedence across overlays.

## Desired End State

While reviewing a card whose back is revealed and whose fragment still resolves,
the reviewer opens a source view showing that fragment marked inside the note text
that precedes and follows it, scrolls it, expands it to the whole note, and returns
to the card with one Esc. Grading is unchanged by any of it. When the fragment
cannot be found, no route is offered and nothing is said about its absence.

Verified by: the acceptance scenarios for US-10 and US-11 passing; the remember
domain suite passing with new pins proving a reveal event consumes no showing and
shifts no draw; the source route returning nothing for an unrevealed card and for
a card whose note no longer contains its quote.

### Key Discoveries:

- Every review event today is a `Grade` or a `Rejected`, so narrowing
  `_showing_count`/`_draw_seed` to grading outcomes changes no existing test result
  — including the pinned draw-seed tests (`backend/tests/unit/remember/test_sitting.py:310-318`,
  `352-361`, `375-392`) and the showing-limit test (`test_sitting.py:159-168`).
- `SchedulingReplay.replay` already filters with `isinstance(outcome, Grade)`
  (`backend/src/domain/remember/ports.py:99`), so a third `ReviewOutcome` member
  is skipped by the scheduler without any change there.
- `ReviewOutcome = Grade | Rejected` is a plain union of `StrEnum`s validated by
  pydantic smart-union (`backend/src/domain/remember/value_objects.py:24`,
  `backend/src/domain/remember/review_event.py:11`). A third member is safe only
  because its string value collides with nothing.
- `RejectCardCommand` is the structural template for a new writing command:
  `uow_factory`/`catalog`/`clock` injection, one `clock.now()` per handler,
  `sitting.guard_outcome(...)`, port writes, then `uow.commit()` inside the
  `async with` (`backend/src/application/remember/commands/reject_card.py:12-42`).
- A new domain exception gets an HTTP status only by a manual entry in
  `EXCEPTION_STATUS_MAP` (`backend/src/adapters/http/errors.py:6-58`); omission
  silently falls back to 500.
- The TUI highlights by wrapping a sliced substring in raw ANSI inverse escapes
  inside one `<Text>` (`tui/src/screens/NoteDetailScreen.tsx:10-11, 23-42`), not
  with Ink props.
- `tui/src/api/sittings.ts` routes errors through `throwOnClientError` into a typed
  `SittingHttpError` (`sittings.ts:53-59, 171-183`); `notes.ts`/`cards.ts` use plain
  `Error`. The source client belongs to the `sittings.ts` tier.

## What We're NOT Doing

- Not touching the browse-path jump from a card detail screen to its note.
- Not redefining how a quote is matched against note text; this change consumes
  `NoteDocument.locate` as it stands.
- Not changing what a card stores about its origin at mint time.
- Not telling the user, anywhere, that a card's source stopped being findable.
  Inside a sitting the absence is silent; reporting drift elsewhere is another change.
- Not saying anything about how soon a note's change is reflected in the route's
  availability — the product exposes no way to edit or delete a note at all.
- Not distinguishing a deleted note from a moved quote. Both are one condition:
  the source cannot be reached.
- Not recording that the user visited the source. A visit leaves no trace on the
  sitting, the schedule, or the review log.
- Not building general TUI scrolling. Phase 9 builds a viewport for the source view
  only; the browse path keeps its current overflow behaviour.

## Implementation Approach

Four movements, in order.

**The domain rule first (Phases 1-2).** Give `ReviewOutcome` a third member and
teach `Sitting` that "how many times was this card shown" means "how many times was
it accounted for", not "how many events mention it". This lands before anything
emits the new outcome, so it is a self-contained correction with its own pins.

**The source as a second boundary crossing (Phases 3, 5).** `CardSourceLocator` is
a new port in the remember domain, implemented by an adapter that sits beside
`InMemoryReviewCatalog` and, like it, is allowed to read distill. Resolution happens
there — the remember domain never imports `NoteDocument`.

**Reveal becomes a write (Phase 4), and the route reads that fact (Phase 6).**
Because the aggregate stays frozen and write-once, the fact lands in the existing
`ReviewEventStore` as a `Revealed` outcome. The source route refuses a card with no
reveal event, which is what enforces AC-18 without inventing reveal state on `Sitting`.

**The client last (Phases 7-9).** One new API call, a nested view inside
`SittingOverlay` that extends the existing Esc ladder, and a viewport so the
expanded state genuinely reaches the whole note.

Phase 10 closes the loop with acceptance scenarios for US-10 and US-11.

## Critical Implementation Details

Phase 2 must narrow **both** `_showing_count` and `_draw_seed`. Narrowing only the
first leaves a reveal event shifting the hash that picks the next card, which would
let the current card change under the user between two `current-card` calls — the
opposite of the "stable next draw" that query promises.

Phase 4 changes `GET .../back` to `POST .../back`. The response shape does not
change, but `tui/src/api/generated/schema.d.ts` is generated from the live OpenAPI
document and must be regenerated against a running backend, or the client will not
typecheck.

---

## Phase 1: Outcome vocabulary

### Overview

Introduce the third review outcome and the vocabulary that separates accounting
outcomes from the rest. Nothing emits or reads it yet.

### Changes Required:

#### 1. Review outcome value objects

**File**: `backend/src/domain/remember/value_objects.py`

**Intent**: Give the review log a way to say "the user saw this back" without that
statement being mistaken for a grading.

**Contract**: New `Revealed(StrEnum)` with a single member `REVEALED = "revealed"`.
`ReviewOutcome` widens to `Grade | Rejected | Revealed`. New module-level
`GRADING_OUTCOMES: frozenset[ReviewOutcome]` holding every `Grade` member plus
`Rejected.REJECTED` — the outcomes that count as a card having been accounted for.
`FINISHING_OUTCOMES` is unchanged and does not gain `Revealed.REVEALED`.

```python
class Revealed(StrEnum):
    REVEALED = "revealed"

ReviewOutcome = Grade | Rejected | Revealed

GRADING_OUTCOMES: frozenset[ReviewOutcome] = frozenset({*Grade, Rejected.REJECTED})
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -q` passes unchanged
- `cd backend && uv run basedpyright src/domain/remember` reports no new errors

---

## Phase 2: Narrow showing count and draw seed to accounting outcomes

### Overview

Teach `Sitting` that a non-grading event neither consumes a showing nor perturbs
the draw. Today's behaviour is unchanged because today every event is a grading;
the pins added here are what keep it that way.

### Changes Required:

#### 1. Sitting aggregate

**File**: `backend/src/domain/remember/sitting.py`

**Intent**: "How many times was this card shown" must mean "how many times was it
accounted for". Counting every event that mentions a card was only ever correct by
accident of there being one kind of event.

**Contract**: `_showing_count` counts only events whose `outcome in GRADING_OUTCOMES`.
`_draw_seed` filters its sorted event list to the same set before hashing, so the
seed is a function of gradings alone. `_card_is_finished`, `next_card`,
`is_finished`, `outstanding`, `_eligible_pool` and `guard_outcome` keep their
current signatures and read the narrowed helpers.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/test_sitting.py -q` passes with existing tests unmodified
- `cd backend && uv run pytest tests/property/remember -q` passes
- `cd backend && uv run pytest tests/unit/remember tests/integration -q` passes

---

## Phase 3: Source port, DTO, route and wiring

### Overview

Materialize every backend symbol Phases 4-6 will implement and test against: the
source value objects, the port, the adapter skeleton, the DTO, the route, and the
composition wiring.

### Changes Required:

#### 1. Source value objects and port

**File**: `backend/src/domain/remember/ports.py`

**Intent**: Give remember its own vocabulary for "where this card came from", so
the route and the tests can be written against a remember concept rather than a
distill one.

**Contract**: New frozen models `SourceSpan` (`block_index: int`, `start: int`,
`end: int`), `SourceBlock` (`index: int`, `text: str`) and `CardSource`
(`blocks: Sequence[SourceBlock]`, `span: SourceSpan`). New Protocol:

```python
class CardSourceLocator(Protocol):
    async def locate(self, card_id: CardId) -> CardSource | None: ...
```

`None` is the single condition covering an absent note and a quote that no longer
matches. `ReviewableCard` is unchanged.

#### 2. Adapter skeleton

**File**: `backend/src/adapters/out/in_memory/remember/card_source_locator.py`

**Intent**: The second — and deliberately second, not hidden — place where distill
is read from remember.

**Contract**: `InMemoryCardSourceLocator(note_repository, card_repository)` with
`async def locate(self, card_id) -> CardSource | None` raising `NotImplementedError`.
Module docstring names the boundary, in the manner of `review_catalog.py:10-14`.

#### 3. Command module move

**File**: `backend/src/application/remember/commands/reveal_back.py`

**Intent**: Reveal stops being a query before it starts writing, so no name on the
path suggests a read model.

**Contract**: Module moved from `application/remember/queries/reveal_back.py`.
`class RevealBackCommand` with `__init__(self, uow_factory, catalog, clock)` and
`async def handle(self, sitting_id, card_id) -> RevealedCardDTO`, body still the
current read-only implementation. The old query module is deleted.

#### 4. DTO, route and wiring

**File**: `backend/src/application/remember/dto.py`, `backend/src/adapters/http/remember.py`, `backend/src/adapters/compose.py`, `backend/src/adapters/http/errors.py`, `backend/src/domain/remember/exceptions.py`

**Intent**: Put the HTTP surface in place so Phase 6 implements behaviour rather
than plumbing.

**Contract**: New `CardSourceDTO` (`blocks: list[SourceBlockDTO]`, `span: SourceSpanDTO`).
New route `GET /review-sittings/{sitting_id}/cards/{card_id}/source` returning
`CardSourceDTO`, raising `NotImplementedError` for now. The `reveal_back` route
becomes `@router.post(...)` on the same path, bound to `Depends(get_reveal_back_command)`.
`compose.py` gains a `_remember_card_source_locator` singleton and
`get_card_source_locator()`; `get_reveal_back_query` is renamed
`get_reveal_back_command` and switched to `uow_factory=_remember_unit_of_work`.
New `SourceNotAvailableError(NotFoundError)`, registered in `EXCEPTION_STATUS_MAP`
as `"source_not_available": 404`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src` reports no new errors
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run pytest tests/integration/test_remember_routes.py -q` passes with the reveal calls switched to POST

---

## Phase 4: Revealing the back records the fact

### Overview

Turn reveal into a write. The aggregate stays frozen and write-once; the fact lands
in the existing review log as a `Revealed` outcome, idempotent per card per sitting.

### Changes Required:

#### 1. Reveal command

**File**: `backend/src/application/remember/commands/reveal_back.py`

**Intent**: AC-18 needs a domain fact saying the back was seen. The review log
already exists and, after Phase 2, ignores non-grading outcomes everywhere it matters.

**Contract**: `handle` opens `self._uow_factory()` as an async context manager,
resolves the sitting (`SittingNotFoundError` when absent), refuses an unoffered
sitting (`SittingExpiredError`) and a non-member card (`CardNotInSittingError`),
resolves the card through the catalog (`CardNotReviewableError` when absent), then
appends a `ReviewEvent(card_id=…, reviewed_at=clock.now(), outcome=Revealed.REVEALED,
sitting_id=…)` and commits. Idempotent: when the sitting's events already carry a
`Revealed` outcome for this card, no second event is written and the same
`RevealedCardDTO` is returned. `guard_outcome` is deliberately **not** called —
revealing is not an outcome and must not be refused for a finished sitting.

#### 2. Client call

**File**: `tui/src/api/sittings.ts`, `tui/src/api/generated/schema.d.ts`

**Intent**: Follow the verb change; the response shape is unchanged.

**Contract**: `revealBack` switches `client.GET` to `client.POST` on the same path.
`schema.d.ts` regenerated via `pnpm generate:api` against a running backend.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/test_reveal_back_command.py -q` passes
- `cd backend && uv run pytest tests/unit/remember tests/integration -q` passes
- `cd tui && pnpm vitest run test/sittings.test.ts test/sittingStore.test.ts` passes
- `cd tui && pnpm typecheck` passes

#### Manual Verification:
- With the backend running, `curl -s -X POST localhost:8000/review-sittings/$SID/cards/$CID/back | jq` returns the back, and repeating it leaves exactly one reveal event in the log

---

## Phase 5: The locator resolves the fragment

### Overview

Implement the adapter: read the card's quote and its note, run distill's grounding,
and return the note's blocks with the located span — or nothing.

### Changes Required:

#### 1. Locator adapter

**File**: `backend/src/adapters/out/in_memory/remember/card_source_locator.py`

**Intent**: Resolution belongs where both contexts are already visible, so the
remember domain never imports distill's document model.

**Contract**: `locate` finds the live distill card by id, reads its note, builds
`NoteDocument.of(note.content)` and calls `locate(card.anchor)`. On an `EXACT` or
`BLOCK` resolution it returns a `CardSource` carrying **every** block of the note
(not filtered, unlike the browse path) plus a `SourceSpan` mapped from the
`AnchorLocation`. It returns `None` when the card is absent, discarded, its note is
absent, or the anchor does not resolve.

#### 2. Port contract suite

**File**: `backend/tests/unit/remember/contracts/test_card_source_locator_contract.py`

**Intent**: The port earns the same behavioural suite every other remember port has.

**Contract**: `_IMPLEMENTATIONS: list[Callable[[], CardSourceLocator]]` parametrized
`ids=["in_memory"]`, per `context/foundation/rules/contract-testing.md`. The
unresolvable case is constructed by saving a note whose content no longer contains
the card's quote back into the in-memory note repository after the card was minted.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/contracts/test_card_source_locator_contract.py -q` passes
- `cd backend && uv run pytest tests/unit/remember -q` passes
- `cd backend && uv run basedpyright src/adapters/out/in_memory/remember` reports no new errors

---

## Phase 6: The source route and the AC-18 gate

### Overview

Wire the route to the locator and the reveal fact. No reveal, no source. No
resolution, no source. Both answer identically from the client's side.

### Changes Required:

#### 1. Source query

**File**: `backend/src/application/remember/queries/card_source.py`

**Intent**: One place decides whether the route exists for this card right now.

**Contract**: `CardSourceQuery(sittings, events, locator, clock)` with
`async def handle(self, sitting_id, card_id) -> CardSourceDTO`. Raises
`SittingNotFoundError`, `SittingExpiredError` and `CardNotInSittingError` as the
other read paths do. Raises `SourceNotAvailableError` when the sitting's events
carry no `Revealed` outcome for this card, and equally when `locator.locate`
returns `None` — the two conditions are indistinguishable in the response, by design.

#### 2. Route

**File**: `backend/src/adapters/http/remember.py`, `backend/src/adapters/compose.py`

**Intent**: Expose the query behind the path Phase 3 reserved.

**Contract**: The `/source` route delegates to `CardSourceQuery` via
`Depends(get_card_source_query)`. `compose.py` gains that provider, built from
`_remember_sittings`, `_remember_review_events`, `_remember_card_source_locator`
and `_remember_clock`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/test_card_source_query.py -q` passes
- `cd backend && uv run pytest tests/integration/test_remember_routes.py -q` passes
- `cd backend && uv run pytest -q` passes

#### Manual Verification:
- Open a sitting, then `curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/review-sittings/$SID/cards/$CID/source` returns 404 before the back is revealed and 200 after

---

## Phase 7: TUI client, view state and viewport component

### Overview

Materialize every client symbol Phases 8-9 implement against.

### Changes Required:

#### 1. API client

**File**: `tui/src/api/sittings.ts`

**Intent**: One call, in the tier that already raises typed sitting errors.

**Contract**: New types `SourceSpan` (`blockIndex`, `start`, `end`) and `CardSource`
(`blocks: { index: number; text: string }[]`, `span: SourceSpan`). New
`fetchCardSource(sittingId, cardId): Promise<CardSource | null>` calling
`client.GET("/review-sittings/{sitting_id}/cards/{card_id}/source", …)`, returning
`null` on a 404 and routing every other failure through `throwOnClientError`.

#### 2. Overlay view state

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: The source view is a nested view inside the overlay, following the
`isRejectConfirmPending` precedent rather than global store state.

**Contract**: Local state
`sourceView: { source: CardSource; isExpanded: boolean; offset: number } | null`
and `isSourceAvailable: boolean`, plus the constants for the new hints. Handlers
declared, bodies unimplemented.

#### 3. Viewport component

**File**: `tui/src/components/SourceViewport.tsx`

**Intent**: The first scrollable surface in this codebase; kept as its own component
so nothing else inherits it by accident.

**Contract**:
`SourceViewport({ lines, offset, height }: { lines: string[]; offset: number; height: number }): JSX.Element`
rendering a window plus "more above"/"more below" markers. Unimplemented body.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck` passes
- `cd tui && pnpm lint` passes
- `cd tui && pnpm vitest run` passes unchanged
- `cd tui && pnpm build` completes, confirming the new modules resolve

---

## Phase 8: The source view and the Esc ladder

### Overview

Open the source on a keypress once the back is revealed, render the fragment marked
inside surrounding note text, and make Esc close the source before the sitting.

### Changes Required:

#### 1. Source view rendering and key routing

**File**: `tui/src/screens/SittingOverlay.tsx`, `tui/src/components/DueOverlayFooter.tsx`

**Intent**: A read-only excursion with exactly one way out, offered only when it
leads somewhere.

**Contract**: After a successful reveal the overlay calls `fetchCardSource` once and
sets `isSourceAvailable` from whether it returned a source. `s` opens the source view
only when `isBackVisible && isSourceAvailable`; nothing is rendered or said when it
is unavailable. While `sourceView !== null`: Esc closes it and returns to the card,
leaving the sitting open; grade digits, arrows, `t`, `x` and Enter are all inert.
The Esc chain in `useInput` becomes source view → reject confirm → close sitting.
The fragment is marked by slicing `block.text` at `span.start`/`span.end` and
wrapping it in the same ANSI inverse escapes `NoteDetailScreen.tsx:23-42` uses.
Blocks before the span's block are rendered, not filtered out. The footer gains a
source hint, shown under the same condition that enables the key.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sittingOverlay.test.tsx` passes
- `cd tui && pnpm vitest run` passes
- `cd tui && pnpm typecheck` passes

#### Manual Verification:
- `cd tui && pnpm start`, open a review, press `t` then `s`: the fragment appears highlighted with text above and below it; Esc returns to the card with the sitting intact; a second Esc leaves the sitting

---

## Phase 9: Expansion and the viewport

### Overview

Make the whole note genuinely reachable: a scrollable window, and an expanded state
that is a second state of the same view rather than a destination.

### Changes Required:

#### 1. Viewport

**File**: `tui/src/components/SourceViewport.tsx`

**Intent**: Without this, "the whole note is reachable" is false for any note longer
than the terminal.

**Contract**: Renders `lines.slice(offset, offset + height)` with a "more above"
marker when `offset > 0` and "more below" when `offset + height < lines.length`.
Pure presentation; the offset is owned by the caller.

#### 2. Expansion and offset

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: Expansion is a second state of one view, so it costs no network call and
exits by the same single gesture.

**Contract**: In the source view, up/down arrows move `offset` by one line and page
keys by `height`, clamped to `[0, max(0, lines.length - height)]`. `e` toggles
`isExpanded`: collapsed shows the span's block with its neighbours, expanded shows
every block. Toggling resets `offset` so the span stays in view. Esc still returns
to the card from either state — never from expanded to collapsed. `height` derives
from the same `stdout.rows` the overlay already sizes itself with (`App.tsx:29-31`).

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sourceViewport.test.tsx test/sittingOverlay.test.tsx` passes
- `cd tui && pnpm vitest run` passes
- `cd tui && pnpm lint` passes

#### Manual Verification:
- `cd tui && pnpm start` with a note longer than the terminal: press `s` then `e`, scroll to the last line, confirm the "more below" marker disappears there and that Esc from the expanded state lands on the card

---

## Phase 10: Acceptance scenarios for US-10 and US-11

### Overview

Express AC-18, AC-19 and AC-20 as scenarios, including the condition the product
cannot itself produce.

### Changes Required:

#### 1. Feature and steps

**File**: `backend/tests/features/remember-flow/US-10-get-to-where-the-card-came-from.feature`, `backend/tests/features/remember-flow/US-11-a-note-edit-never-costs-a-card.feature`, `backend/tests/bdd/steps/remember_review.py`

**Intent**: Close the traceability chain from the effort's acceptance criteria to
executable scenarios.

**Contract**: US-10 covers reaching the fragment after the back is revealed, and its
absence before. US-11 covers a card whose fragment no longer resolves still being
presented and graded, with no route offered and no message. The unresolvable state
is built by rewriting the note in the in-memory repository after the card was minted
— the product has no edit or delete route. Steps are appended to `remember_review.py`
and registered per the existing `pytest_plugins` convention.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/features -q` passes
- `cd backend && uv run pytest tests/bdd/test_remember_step_coverage.py -q` passes
- `cd backend && uv run pytest -q` passes

---

## Testing Strategy

### Unit Tests:
`Sitting` gains pins that a reveal event consumes no showing, finishes no card and
shifts no draw. `RevealBackCommand` gains event-write and idempotency tests.
`CardSourceQuery` gains gate tests for unrevealed and unresolvable. TUI store and
component tests cover the view state, the Esc ladder and the viewport reducer.

### Integration Tests:
`test_remember_routes.py` covers the POST reveal, the source route's 404/200 split,
and that grading is unaffected by whether the source was fetched. `CardSourceLocator`
gets the standard parametrized contract suite, with the unresolvable case built by
rewriting the note behind the card.

### Manual Testing Steps:
Per phase above; the load-bearing one is Phase 9 with a note longer than the terminal.

## Performance Considerations

The source route returns every block of the note. Notes are user-authored and
single-file; no pagination is warranted. The route is called once per reveal, not
per keystroke, and the expanded state costs no further call.

## Migration Notes

No data migration. `GET .../back` becomes `POST .../back` — a breaking change to a
route with exactly one consumer, updated in the same phase. Existing review event
logs stay valid: they contain only grading outcomes, which is precisely what
Phase 2 narrows to.

## References

- Frame: `frame.md`, `frame-log.md`
- Research: `research.md`
- Acceptance: `context/efforts/remember-flow/stories.md:97-112`
- Requirements: `context/efforts/remember-flow/prd.md:65`
- Anchor ADR: `context/adrs/distill-domain-shape/decision.md:40-46`
- Execution state: `todos.md`
