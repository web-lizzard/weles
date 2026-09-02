---
feature: "Distill flow"
effort_id: distill-flow
version: 1
status: draft
created: 2026-09-02
context_type: greenfield
---

## Problem & Outcome

The Weles user finishes a capture session, approves the drafted note, and nothing happens. The approved note becomes an outbox envelope that no one consumes: it cannot be read back inside Weles, nothing is derived from it, and the middle pillar of `capture → distill → remember` is an empty pipe — capture produces into nowhere and remember has nothing to live on. The cost is precisely the failure the product exists to fix: notes pile up without compounding, which is the "second junk drawer" `project-overview.md` names as the thing Weles must not be.

When this ships, an approved note becomes — with no user action — a note Weles holds and a set of flashcards grounded in that note's own text. The user can list what they have captured, open a note and read it, see the cards it produced, and jump from any card to the exact fragment of the note it was derived from.

## User & Persona

The single Weles user — one person working through technical material (books, courses, projects). They reach for this right after closing a capture session, wanting to see what came out of it, or later, wanting to return to an earlier note and check what it yielded.

## Success Criteria

### Primary
- An approved capture note appears in Weles as a note with its flashcards, with no manual step by the user in between.
- From the note list the user can see that cards came into existence and which note each set belongs to.

### Secondary
- Most generated proposals survive the grounding check — a low rejection rate is the only quality signal available before the review flow exists.
- Returning to a captured note inside Weles is faster than going back to the original source material.

### Guardrails
- A card never contains anything the note does not support.
- Browsing notes and cards never interrupts or discards an in-flight capture session.
- The same approved note never appears twice, however many times its approval is delivered.
- A note that yields zero cards is a correct outcome, not a failure — the product's own filter says not every note deserves memorizing.

## Functional Requirements

### Note intake

- FR-001: An approved capture note becomes a note held by Weles automatically, with no user action. Priority: must-have

### Card generation

- FR-002: Weles generates flashcards from a held note automatically, without the user asking for them. Priority: must-have
- FR-003: Every generated card cites the verbatim fragment of the note it was derived from. Priority: must-have
- FR-004: A proposed card whose cited fragment cannot be found in the note never reaches the user. Priority: must-have
- FR-005: A note that produces zero cards is reported as a completed distillation, not a failed one. Priority: must-have
- FR-006: Proposals rejected during generation are retained rather than dropped, so the rejection rate stays observable. Priority: must-have

### Browsing notes and cards

- FR-007: User can list their notes without leaving or losing an in-flight capture session. Priority: must-have
- FR-008: The note list shows, per note, its topic, its distillation state, and how many cards it has. Priority: must-have
- FR-009: The note list is ordered by the most recent update of a note or of its cards. Priority: must-have
- FR-010: The distillation state distinguishes three cases: generation in progress, completed with zero cards, and generation failed. Priority: must-have
- FR-011: User can open a note and read its full content inside Weles. Priority: must-have
- FR-012: User can see the cards generated from an open note. Priority: must-have
- FR-013: User can jump from a card to the fragment of the note it came from, with that fragment marked in the note view. Priority: must-have
- FR-014: User is told once, when a note's cards become ready, rather than having to notice the state change on the list. Priority: nice-to-have

## Non-Goals

- The entire spaced-repetition layer — scheduling, review sessions, due dates, review reminders, and any state about how well a card is known. That is the `remember` pillar and its own effort.
- Manual removal or curation of generated cards. The user's call: turning a card down is a review-time gesture and belongs with `remember`. Cost recorded in Open Questions 1.
- Regeneration of a note's cards. Re-running generation on unchanged input produces nothing new; a meaningful trigger only exists once notes can be amended.
- Editing or amending a note after Weles holds it. Notes are born in capture and arrive already approved.
- Publishing notes to an external workspace. Deferred, not reversed — it adds a write target later without changing what this ship produces.
- A surface for inspecting rejected proposals. They are retained (FR-006) but nothing reads them back yet.
- Semantic search across notes and cards. A separate product promise with its own scope.
- Notes originating anywhere other than a capture session. One birth path keeps intake to a single contract.
- The one-time "cards are ready" message (FR-014). The state badge on the note list already carries the fact; the message only makes it arrive sooner.

## Open Questions

1. **`user_audit` has no caller once manual card removal is out of scope.** The `distill-domain-shape` ADR cut an earlier value on exactly the grounds that nothing could set it, and justified `user_audit` by manual removal being in scope. The ADR is `open`, so an amendment is the route. — Owner: user. Block: no.
2. **How is a cited fragment matched against the note's content** so that an honest card is not rejected over formatting alone? — Owner: implementation, resolved at `/plan`. Block: no.
3. **A note can sit in "generation in progress" forever** — there is no timeout and no sweeper. Does the user need a way to retry generation, or is a visible failed state enough? — Owner: user. Block: no.
4. **By what gesture does the user reach the note list** — the command set for the shell is not settled. — Owner: implementation, resolved at `/plan`. Block: no.
