# Source Jump During Review — Plan Brief

> Full plan: `plan.md`

## What & Why

A card under review can be ambiguous, and today there is no way to see the note
fragment it was drawn from without abandoning the sitting. This change adds a
read-only source view reachable from the card, and defines the one case where that
route is absent: the fragment can no longer be found.

## Starting Point

Anchors ship end-to-end in distill, but `InMemoryReviewCatalog` deliberately strips
them at the remember boundary — `ReviewableCard` is `id`/`front`/`back` only.
Revealing a back is a stateless read that nothing records.

## Desired End State

With a card's back revealed and its fragment still resolving, the reviewer opens a
source view showing that fragment marked inside surrounding note text, scrolls it,
expands it to the whole note, and returns to the card with one Esc. Grading is
unaffected either way. When the fragment cannot be found, no route is offered and
nothing is said about its absence.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Route availability | Gated on the back being revealed | The source passage is a superset of the back, so an earlier route would answer the card for the user. | Frame |
| Missing fragment | Route absent, not degraded | AC-20 says the jump becomes unavailable; matching distill's "reached anyway, without a highlight" would restate an AC into its opposite. | Frame |
| Source view shape | Dead end, two states, one exit | A sitting must stay workable in one pass; a navigable note screen would give the reviewer a side exit out of the review. | Frame |
| How the card carries its source | A separate `CardSourceLocator` port | Keeps the source path off the hot grading path and gives it its own contract suite. | Plan |
| Who resolves the quote | The remember adapter, via `NoteDocument.locate` | Keeps the remember domain from importing distill's document model, as `InMemoryReviewCatalog` already does. | Plan |
| Where the reveal fact lives | A `Revealed` outcome in the existing review log | Leaves `Sitting` frozen and write-once; the event store already exists and the scheduler already skips non-gradings. | Plan |
| Showing count and draw seed | Narrowed to accounting outcomes | Counting every event was only correct while every event was a grading; a third outcome would silently finish cards and shift the draw. | Plan |
| HTTP verb for reveal | `POST .../back`, `RevealBackCommand` | Once reveal writes, a GET would lie about it and any retry or prefetch would append an event. | Plan |
| Source payload | Whole note blocks plus the located span | Expansion stays a client-side state change, so it is not navigation. | Plan |
| Long notes | A viewport built for the source view | Without scrolling, "the whole note is reachable" is false for any note longer than the terminal. | Plan |

## Scope

**In scope:** reaching a card's source passage from inside a review sitting; the
behaviour of that route when the passage cannot be found; the domain correction that
makes a non-grading event safe; a scrollable source view in the TUI.

**Out of scope:** the browse-path jump that already ships in distill; redefining
quote matching; changing what a card stores at mint time; telling the user anywhere
that a source stopped being findable; any statement about staleness; recording that
the user visited the source; general TUI scrolling beyond the source view.

## Architecture / Approach

The remember domain gains a third review outcome and a `CardSourceLocator` port.
Resolution happens in an adapter beside `InMemoryReviewCatalog` — the one other
place allowed to read distill. Revealing a back becomes a command that appends a
`Revealed` event, which is what the source route checks before answering; the
`Sitting` aggregate stays frozen and write-once. The TUI adds one call, a nested
view inside `SittingOverlay` extending the existing Esc ladder, and the codebase's
first scrollable component.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Outcome vocabulary | `Revealed` member, `GRADING_OUTCOMES` | A colliding enum value would break pydantic's smart union |
| 2. Narrow count and seed | Non-gradings stop consuming showings and shifting draws | Narrowing only one of the two leaves the draw unstable |
| 3. Source port and wiring | VOs, port, adapter skeleton, DTO, route, command move | A missing `EXCEPTION_STATUS_MAP` entry silently becomes a 500 |
| 4. Reveal records the fact | `RevealBackCommand`, `POST .../back` | Regenerating the OpenAPI client needs a running backend |
| 5. Locator resolves | Adapter plus contract suite | The unresolvable case cannot be reached through the product |
| 6. Source route and gate | Unrevealed and unresolvable answer alike | Two conditions must stay indistinguishable to the client |
| 7. TUI stubs | Client, view state, viewport signature | — |
| 8. Source view and Esc ladder | Highlight, gating, one-level Esc | Esc must not abandon the sitting from an open source view |
| 9. Expansion and viewport | Scrolling, full-note state | First scrollable surface in the codebase |
| 10. Acceptance | US-10 and US-11 scenarios | Unresolvable state must be built by fixture |

**Prerequisites:** none — `frame.md` is closed and `research.md` is in hand.

**Estimated effort:** large; six backend phases and three TUI phases, of which
Phase 9 is genuinely new ground.

## Open Risks & Assumptions

- Phase 2 is asserted to be behaviour-preserving because every stored event today is
  a `Grade` or a `Rejected`. If any other event exists in a live store, showing
  counts change for those cards.
- AC-19/AC-20 describe a state the product cannot produce — there is no note edit
  and no note delete anywhere in the stack. Every scenario for it is built through a
  repository fixture, so it tests the rule rather than a user-reachable path.
- After this change the same card and note behave differently in browse and in
  review when a fragment is missing. That divergence is deliberate and recorded in
  `frame.md`; a later reviewer may read it as an inconsistency.
- `POST .../back` is a breaking route change. The TUI is the only known consumer.

## Success Criteria (Summary)

- From a card whose back is revealed, the reviewer reaches the source fragment
  marked in context, reaches the whole note from there, and returns with one Esc.
- A card whose fragment cannot be found is still presented and graded, with no route
  offered and nothing said about its absence.
- A reveal consumes no showing, finishes no card, and does not shift the next draw.
