---
status: draft
version: 3
created: 2026-09-09
effort_id: remember-flow
---

# Remember flow — User Stories

> Revision 2 (2026-09-09): adds US-12 over the PRD's new FR-017 and FR-018, covering entry into a review from an in-flight capture session and the guarantee that free text cannot trigger one. Purely additive — US-01 through US-11 and AC-01 through AC-20 are unchanged. Prior version: stories-versions/v1-stories.md

> Revision 3 (2026-09-11): brings FR-014 under US-09 as AC-23, so the user/generation-time distinction on a rejection has an acceptance authority instead of sitting uncovered. Purely additive — US-01 through US-12 and AC-01 through AC-22 are unchanged. Prior version: stories-versions/v2-stories.md

## Stories

### US-01 — Everything due, in one command

I want one command to open a review covering every card that is due, so that "what do I have to go over today" is a single gesture and an empty day gets a straight answer instead of an empty session.

Realizes: FR-001, FR-006

- AC-01: Starting a review opens a session containing every card that is due at that moment.
- AC-02: Starting a review when nothing is due tells the user so and creates no session.

### US-02 — Answer before you are shown it

I want to see a card's front and reach its back only when I ask for it, so that a review is an attempt at recall rather than another read-through.

Realizes: FR-002, FR-003

- AC-03: A card's back stays hidden until the user chooses to reveal it.
- AC-04: Exactly one card is in front of the user at a time.
- AC-05: After revealing the back, the user records their recall as one of four steps.

### US-03 — Never pick a date

I want a grade to set when a card next comes up, so that keeping the schedule is never my job and well-known cards return less and less often.

Realizes: FR-004

- AC-06: Grading a card sets when it next comes up, without the user naming a date.
- AC-07: A card graded well repeatedly returns after progressively longer gaps.
- AC-08: Grading a card leaves its front and back unchanged.

### US-04 — The one you missed comes back before you stand up

I want a card I graded lowest to return within the same sitting, so that I never finish a review having failed something I will not touch again for days.

Realizes: FR-005

- AC-09: A card given the lowest grade is presented again before the sitting ends.

### US-05 — Walking away costs nothing

I want to leave a review at any point and come back to it later, so that stopping mid-way is an ordinary gesture rather than a loss.

Realizes: FR-007, FR-008

- AC-10: Grades given before the user leaves a session still count afterwards.
- AC-11: The user can return to a session they left and continue with the cards from it still outstanding.

### US-06 — What is offered to resume is still worth resuming

I want a session left untouched long enough to stop being offered, so that the resume list never hands me a batch chosen against a picture that has since moved.

Realizes: FR-009

- AC-12: A session left untouched long enough is no longer offered for resumption.
- AC-13: Grades given in a session that stopped being offered still count toward the schedule.

### US-07 — See what is waiting without sitting down

I want to see how many cards are due without opening a review, so that deciding whether to sit down costs nothing.

Realizes: FR-010, FR-011

- AC-14: The user can see how many cards are due without a review session being started.
- AC-15: While Weles is open, that number keeps up with cards becoming due, without the user leaving and re-entering the view.

### US-08 — Told at the moment capture ends

I want to hear about waiting cards as a capture session closes, so that I learn it at the one moment I am already in Weles and free to switch gears.

Realizes: FR-012

- AC-16: On closing a capture session, the user learns whether cards are waiting to be reviewed.

### US-09 — Turn down a bad card where you meet it

I want to reject a card during a review, so that a bad card leaves circulation instead of coming back to be graded lowest over and over, and so that my turning it down is not confused with the system having thrown it out on its own.

Realizes: FR-013, FR-014

- AC-17: A card the user rejects during a review is not offered in any later review.
- AC-23: A card the user rejects is recorded as the user's own judgement, distinguishable from a card the system rejected when it was generated.

### US-10 — Get to where the card came from

I want to reach the note fragment a card was drawn from while reviewing it, so that an ambiguous card is recoverable by reading its source instead of guessing.

Realizes: FR-015

- AC-18: From a card under review the user reaches the fragment of the note it was drawn from.

### US-11 — A note edit never costs a card

I want a card whose source fragment can no longer be found to stay in circulation, so that editing a note never costs me a card I have been learning.

Realizes: FR-016

- AC-19: A card whose source fragment can no longer be found is still presented and graded.
- AC-20: For such a card the jump to its source becomes unavailable, rather than the card being withheld.

### US-12 — Step into a review without losing the conversation

I want to open a review from inside a capture session and return to the conversation untouched, and never to open one just by talking, so that stepping away mid-capture costs nothing and saying the wrong sentence costs nothing either.

Realizes: FR-017, FR-018

- AC-21: A review opened from within a capture session leaves that conversation intact to return to.
- AC-22: Free text typed into a capture conversation never opens a review.

## Uncovered Requirements

*(none — every FR in `prd.md` is realized by a story.)*
