---
status: closed
created: 2026-09-10
updated: 2026-09-10
---

## Boundaries

**In scope**

- A read-only reading of how many cards are due, obtainable without a review sitting existing or being minted.
- Both ends of that reading: the backend that produces the numbers, and the TUI surface that shows them.
- One number is a total of distinct cards waiting; a breakdown sits inside that total rather than beside it, so no two displayed numbers can be added into a wrong result.
- The breakdown's axis is **why a card is waiting**: not yet seen · seen and still owed · ripe but outside the open sitting. With no sitting live, every due card is *not yet seen* and the other buckets are zero.
- Whatever shell change is needed for the total to remain visible while a review is open. Exactly where it sits on screen is a planning detail; that it survives an open overlay is not.
- The breakdown's presentation inside the review overlay, which today shows only an outstanding count.

**Out of scope**

- Minting, resuming, finishing, or otherwise mutating a sitting. Nothing on this path writes.
- Changing what `Sitting` counts as finished (`FINISHING_GRADES`, `showing_limit`) or what the scheduler returns. Carried by `context/changes/remember-flow-scheduler-aware-finish/`, parked behind persistence.
- Any notion of "due" narrower or wider than `card_is_due`. A card with no scheduling record is due, exactly as the scheduler has it.
- The post-capture prompt (S-07 / AC-16) and review entry from capture (S-06 / AC-21, AC-22).
- Card rejection (S-04) and source jump (S-05).

**Design constraints carried here because no acceptance criterion covers them**

- No two numbers on screen disagree about the same cards — neither in meaning nor in time. Every number displayed together comes from one computation, so an interaction that changes one changes all of them.
- Deriving the numbers reads the schedule and the open sitting together, and therefore belongs to neither alone — not to stored state, and not to a method on `Sitting`, which would have to accept scheduling state and reproduce the coupling that is parked out of scope above.

## Requirements

- AC-14
- AC-15
