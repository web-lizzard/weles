---
status: closed
created: 2026-09-10
updated: 2026-09-10
---

## Boundaries

**In scope.** Leaving a review sitting part-way and coming back to that same sitting, plus the horizon after which a sitting stops being offered back. The slice covers AC-10 through AC-13 of the `remember-flow` effort.

A sitting left part-way must be recoverable after the client process has gone away, not only after an in-process navigation away from the review view. The state that makes a sitting findable again is server-side; no client holds authority over which sitting is resumable.

At most one sitting is open for resumption at any moment. Opening a review while such a sitting exists never produces a second one alongside it. The rule is stated globally here because there is exactly one selection axis today; it is expected to be re-scoped, not removed, when a second axis (owner, topic) arrives.

Returning to a review is silent: a user whose open sitting is still within the horizon lands back in it without being asked to choose. What they are shown is the sitting's own outstanding set — its members not yet finished under the rules the sitting opened with — never a set recomputed against the current moment. When a review opens onto a sitting already in progress, the user can tell that they are returning to one rather than starting fresh, and how many of its cards are still outstanding.

A sitting that has passed its horizon is not offered back, and opening a review then produces a fresh sitting over what is due at that moment. Nothing about that costs the user work: a card left ungraded in the expired sitting is still due and is drawn into the new one, while grades already given keep counting. A fresh sitting starts its own per-card showing counts and its own presentation order, exactly as it would after any sitting ends.

**Out of scope.** The sitting's identifier as a user-facing fact — nothing in the interface asks the user to read, hold, or quote it. A "start fresh" mode that abandons an unexpired sitting and opens a new one in its place; it may become a mode later. Scoping any part of the remember flow by owner: no ownership key is introduced on sittings, cards, review events, or scheduling state. Building an authentication or login mechanism — the shape of one is undecided. Every acceptance criterion belonging to another slice on the `remember-flow` roadmap: AC-01 through AC-09 (shipped by S-01), and AC-14 through AC-22 (due count, capture prompt, card rejection, source jump, capture entry).

## Requirements

- AC-10 — from US-05.
- AC-11 — from US-05.
- AC-12 — from US-06.
- AC-13 — from US-06.
