---
feature: "Remember flow"
effort_id: remember-flow
version: 1
status: draft
created: 2026-09-09
context_type: greenfield
---

## Problem & Outcome

Distill produces flashcards and nobody ever sees them again. The user finishes a capture session, the note is distilled, cards come into existence — and they sit in a list that can be browsed but never returns to the user on its own. That is the same "second junk drawer" failure `project-overview.md` names, one floor down: instead of notes nobody rereads, cards nobody repeats. The loop `capture → distill → remember` breaks at the only link that turns written down into retained, so the cost is paid exactly where the product claims its value.

When this ships, one command opens a review over the cards that are due, the user grades their recall, and the schedule moves on its own. Leaving mid-review destroys nothing, and the user can tell there is work waiting without having to guess.

## User & Persona

The single Weles user — one person working through technical material (books, courses, projects). They do not reach for this straight after capture. They reach for it as a separate habit: "what do I have to go over today", opened deliberately, finished when the queue is empty.

## Success Criteria

### Primary
- In one command the user can work through everything due and finish with an empty queue.
- A card's next appearance is derived from the user's own grades, so well-known cards return less and less often.

### Secondary
- Bad cards leave circulation early — rejection during review gets used, rather than a card being graded lowest over and over.
- Leaving a review half-way and coming back later is an ordinary gesture, not a loss.

### Guardrails
- A grade once given is never lost, whatever happens to the session around it.
- The schedule never depends on Weles having been running in between — nothing is missed because the app was closed.
- Reviewing never interrupts or disturbs capture or distillation.
- A card discarded in distill never appears in a review again.
- Reviewing a card changes nothing about its content.

## Functional Requirements

### Review session

- FR-001: User can start a review session with a single command, covering every card that is due. Priority: must-have
- FR-002: A review session presents one card at a time, showing its front before its back. Priority: must-have
- FR-003: User can reveal a card's back and then grade their recall on a four-step scale (forgot / hard / good / easy). Priority: must-have
- FR-004: A graded card is rescheduled automatically; the user never picks a next date. Priority: must-have
- FR-005: A card graded lowest comes back within the same sitting. Priority: must-have
- FR-006: Starting a session when nothing is due tells the user so, rather than opening an empty session. Priority: must-have

### Leaving and returning

- FR-007: User can leave a review session at any point without losing any grade already given. Priority: must-have
- FR-008: User can resume the session they left and continue with the cards still outstanding in it. Priority: must-have
- FR-009: A session left untouched long enough stops being offered for resumption. Priority: must-have

### Knowing there is work

- FR-010: User can see how many cards are due without starting a session. Priority: must-have
- FR-011: That count refreshes while Weles is open, without the user re-entering the view. Priority: must-have
- FR-012: After a capture session closes, user is told if cards are waiting to be reviewed. Priority: nice-to-have

### Judging a card

- FR-013: User can reject a card during a review, so it stops being scheduled. Priority: must-have
- FR-014: A rejected card is recorded as a user's own judgement, distinct from cards rejected at generation time. Priority: must-have
- FR-015: User can jump from a card under review to the note fragment it was derived from. Priority: nice-to-have
- FR-016: A card whose source fragment can no longer be found stays reviewable; only the jump to it becomes unavailable. Priority: must-have

## Non-Goals

- **Topic- or note-scoped selection.** Argued through and deferred: a selection that ignores due-ness forces a second completion policy alongside it, so it costs two capabilities designed together, not one. The default pair (everything × exhaust what is due) delivers the pillar's whole product value.
- **Batch-of-N and timebox session modes.** The other half of the same pair; deferred with it.
- **Statistics, streaks, charts.** Review history exists, but reporting on it is a separate product, not part of making cards come back.
- **FSRS parameter optimization.** There is no body of review history to fit against until the pillar has been used; it is purely additive later.
- **Editing a card during a review.** Fixing a card's wording belongs to distill; from a review the only judgement available is rejection.
- **Notifications outside a running Weles.** Telling the user something is due while the app is closed requires a background process this pillar deliberately does not have.
- **Multiple devices or synchronization.** One person, one machine.

## Open Questions

1. **Exact UI labels for the four grades.** — Owner: user. Block: no (four steps are settled; the wording can land during stories).
2. **How often the due count refreshes while Weles is open.** — Owner: user. Block: no (any sane cadence ships).
3. **The session expiry horizon value.** — Owner: user. Block: no (a configured setting; the number can be tuned after first use).
4. **Whether the post-capture prompt (FR-012) earns its place at all.** — Owner: user. Block: no (nice-to-have; may be dropped rather than built).
