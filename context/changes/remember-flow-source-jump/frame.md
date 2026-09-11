---
status: closed
created: 2026-09-11
updated: 2026-09-11
---

## Boundaries

In scope: reaching a card's source passage from inside a review sitting, and the behaviour of that route when the passage can no longer be found. The source view is a dead end — it presents the note's content and returns to the card under review, and offers no navigation onward to other notes, to a card list, or out of the sitting.

The source view has two states: the fragment with the note text on either side of it, and the note in full. Moving between them is not navigation — both states are read-only, and both leave by the same single exit back to the card. Esc never descends more than one level inside a sitting: from either state it returns to the card under review, never to the other state.

The browse path's behaviour when a fragment cannot be found — reaching the note anyway, without a highlight, and saying so (`tui/src/screens/NoteDetailScreen.tsx:98-100`) — is deliberately not matched here. Browsing is the user examining their own notes; a sitting is the user grading recall. The two modes answer the same missing fragment differently on purpose.

Out of scope: the browse-path jump from a card detail screen to its note, which already ships in distill. Re-deciding how a quote is matched against a note's text — this change consumes the existing grounding semantics and does not redefine them. Changing what a card stores about its origin at mint time. Surfacing to the user, anywhere, that a card's source has stopped being findable — inside a sitting the absence is silent, and reporting the drift elsewhere belongs to a different change. Any statement about how soon a note's change is reflected in the route's availability.

A note that no longer exists and a quote that no longer matches are one condition for this change: the source cannot be reached. Nothing downstream distinguishes them.

Esc must keep meaning "leave the thing that is open" throughout a sitting: while the source view is open it closes that view and returns to the card, and abandoning the sitting is never the outcome of a single Esc pressed against an open source view.

## Requirements

- AC-18 — reachable only once the card's back has been revealed. The source passage is a superset of the back's content, so an earlier route to it would answer the card on the user's behalf.
- AC-18 — the source fragment is marked within the note text that both precedes and follows it, not presented alone; the context leading up to a fragment is usually what makes an ambiguous card recoverable.
- AC-18 — the whole note is reachable from the source view without leaving it.
- AC-19 — grading a card is unaffected by whether its source is reachable, and by whether the user visited the source before grading. A visit leaves no trace: nothing about the sitting, the card's schedule, or what is recorded of the review differs because the user read the source.
- AC-20 — when the fragment cannot be found, the route to the source is absent rather than present-and-inert; the user is not offered a jump that leads nowhere, and is told nothing about its absence.
- AC-18, AC-20 — a card under review carries the identity of the note it was drawn from and the quote it was drawn as. Without both, the route in AC-18 cannot exist and the condition in AC-20 cannot be evaluated.
