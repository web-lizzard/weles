---
effort_id: distill-flow
title: Distill flow
status: preparing
created: 2026-09-02
updated: 2026-09-02
archived_at: null
origin: distill-pillar
adr_refs:
  - id: distill-domain-shape
    kinds: [implements]
---

## Goal

Close the empty middle of `capture → distill → remember`: today an approved capture note becomes an outbox envelope nobody consumes, so it cannot be read back inside Weles and nothing is derived from it. This effort makes an approved note arrive automatically as a note Weles holds, generates flashcards grounded in that note's own text, and gives the user a place to see it — a list of notes carrying topic, distillation state and card count, a readable note, its cards, and a jump from any card to the fragment it came from. It succeeds when an approved note turns into a note with cards without a single manual step, and the user can see from the list that those cards exist and which note they belong to.
