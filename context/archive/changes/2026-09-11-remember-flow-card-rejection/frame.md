---
status: closed
created: 2026-09-11
updated: 2026-09-11
---

## Boundaries

**In scope**

- Rejection is recorded by `remember` as an outcome of meeting a card in a review, in the
  same log that already holds grades — not as a separate registry of rejected cards.
- The durable removal from circulation is a `user_audit` discard held by `distill`, per
  `context/adrs/distill-domain-shape/decision.md:112`. `remember` causes it; it does not
  own it.
- Delivery of that rejection into `distill` is asynchronous, through the existing outbox.
  `remember`'s own record is what covers the window before it lands.
- A rejection never reaches the scheduler. It produces no scheduling state and takes no
  part in a replay of a card's scheduling history.
- A rejected card counts as settled for the sitting it was rejected in: the sitting can
  reach completion without it, and it is not drawn again inside that sitting.
- Rejection becomes available only once the user has seen the card's back — the same gate
  grading sits behind. A card is judged as a pair, and half of it is not enough to judge
  on: a sound front can carry a corrupted back. AC-05 is unaffected, because recall is
  still recorded as one of four steps; rejection is not a recall record.
- Rejection is **best-effort, not guaranteed**. The PRD guardrail *"a grade once given is
  never lost"* does not extend to it. If delivery into `distill` exhausts its attempts and
  the envelope is abandoned, the card returns to circulation and the user rejects it again.
  Nothing reconciles an abandoned delivery, and `remember`'s own record is not consulted as
  a fallback filter when a later review is assembled.

**Out of scope**

- Restoring a rejected card. A discard is terminal
  (`context/adrs/distill-domain-shape/decision.md:81`).
- Any surface for inspecting or reporting on rejections, or for noticing an abandoned one.
- Editing a card during a review — the PRD's Non-Goals keep card wording in `distill`.

## Requirements

- Cites AC-17 — a card the user rejects during a review is not offered in any later review.
- Cites AC-23 — a card the user rejects is recorded as the user's own judgement,
  distinguishable from a card the system rejected when it was generated.
