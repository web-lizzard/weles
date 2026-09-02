---
status: draft
version: 1
created: 2026-09-02
effort_id: distill-flow
---

# Distill flow — User Stories

## Stories

### US-01 — The note lands by itself

I want my approved note to be held by Weles without my doing anything, so that closing a capture session is the last action I take.

Realizes: FR-001

- AC-01: After the user approves a note and takes no further action, that note is among the notes Weles holds.
- AC-02: One approved note is held exactly once, however many times its approval is delivered.

### US-02 — Cards without asking, and nothing is a fine answer

I want cards generated from a held note without my requesting them, and a note that yields none to count as finished, so that distillation is something Weles does rather than a chore I schedule.

Realizes: FR-002, FR-005

- AC-03: Cards exist for a held note without the user having asked for them.
- AC-04: A note that produces no cards ends in the same completed state as one that produced cards, differing only in its card count.

### US-03 — Never a card the note doesn't support

I want every card I see to quote the part of my note it came from, and a card that can't, to never reach me, so that I can trust a card without re-reading the note to check it wasn't invented.

Realizes: FR-003, FR-004

- AC-05: Every card the user can see names a fragment of its note, quoted as the note has it.
- AC-06: A proposed card whose quoted fragment is not present in its note never reaches the user.

### US-04 — Look around without losing the conversation

I want to reach my notes while a capture session is still open, so that checking something earlier doesn't cost me the session I'm in.

Realizes: FR-007

- AC-07: The user can reach their notes while a capture session is in flight and return to that session with nothing lost.

### US-05 — The list says what happened to each note

I want the note list to tell me each note's topic, how its distillation went and how many cards it produced, most recently touched first, so that I can see what came out of my captures without opening them one by one.

Realizes: FR-008, FR-009, FR-010

- AC-08: Each note in the list shows its topic, its distillation state, and how many cards it has.
- AC-09: The list tells apart a note still generating, a note finished with zero cards, and a note whose generation failed.
- AC-10: Notes whose note or cards changed most recently appear before less recently changed ones.

### US-06 — Read the note and what it produced

I want to open a note, read all of it, and see the cards it produced, so that returning to something I captured is faster than going back to the source.

Realizes: FR-011, FR-012

- AC-11: The user can open a note from the list and read its full content inside Weles.
- AC-12: The cards generated from an open note are visible from that note.

### US-07 — Jump from a card to where it came from

I want to get from a card to the exact passage of the note it was drawn from, so that when a card is ambiguous I can recover the context instead of guessing.

Realizes: FR-013

- AC-13: From a card the user reaches its note with the source fragment distinguished from the rest of the content.

### US-08 — Hear it once when the cards are ready

I want to be told the moment a note's cards are ready, so that I don't have to keep returning to the list to find out whether generation finished.

Realizes: FR-014

- AC-14: The user learns that a note's cards are ready without having to be looking at the note list.
- AC-15: That announcement arrives once for a given note and does not repeat on later visits.

## Uncovered Requirements

- **FR-006** — Rejected proposals are retained for a reader that does not exist in this ship; the PRD's own Non-Goals bar the inspection surface. A technical enabler for the Secondary success criterion, with no user-observable pass condition.
