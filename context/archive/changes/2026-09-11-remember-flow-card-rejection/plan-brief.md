# Card Rejection During Review — Plan Brief

> Full plan: `plan.md`

## What & Why

A user meeting a bad card in a review can turn it down, and it stops coming back. Today the
only judgement available in a sitting is a grade, so a bad card gets graded lowest over and
over instead of leaving circulation.

## Starting Point

`remember` has a complete sitting — draw, reveal, grade, reschedule — and no way to express
"this card is bad". `distill` owns removal through `Discard` but has no manual-discard
command, and its `CardRepository` cannot fetch a card by id.

## Desired End State

From a card whose back is revealed, one gesture rejects it. The sitting moves on and never
draws it again; within about a second the outbox delivers a `user_audit` discard into
`distill`, after which the catalog stops offering the card to any sitting.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where rejection lives | `remember`'s review log records it; `distill` holds the `user_audit` discard | The outbox alone leaves remember blind for the poll interval, and its own draw rule favours the card just turned down. | Frame |
| Durability | Best-effort, not guaranteed | The PRD's "a grade is never lost" does not extend to rejection; a dead-lettered envelope returns the card. | Frame |
| Typing the fifth outcome | `outcome: Grade \| Rejected`, named `Rejected` not "discarded" | `Grade` stays four members, so the scheduler stays total by construction; "discard" is `distill`'s word for a boundary this change does not write across. | Plan |
| The window before delivery | Settles the sitting; does not touch the due count | One representation of "out of circulation" when views are assembled, at the cost of a brief over-count. | Plan |
| Finding the card in `distill` | Add `CardRepository.get(card_id)` | `remember` does not know `distill`'s `note_id`, and the catalog is the only place the two vocabularies meet. | Plan |
| Legality gate | Identical to grading's, moved onto `Sitting` | One moment of legality, as the frame settled; one rule instead of two that can drift. | Frame |
| Redelivery | No-op on any existing discard | A discard is terminal, and the three reasons stay disjoint because each feeds a different correction. | Plan |
| HTTP contract | `204`, then re-read `current-card` | Smallest contract; costs a new `currentCard()` client function and a 204 branch the api layer has never needed. | Plan |

## Scope

**In scope:** the fifth outcome in `remember`'s domain and application layers, the outbox
envelope and its `distill` handler, the first manual-discard command in `distill`, the HTTP
route, acceptance scenarios for AC-17 and AC-23, and the TUI gesture behind the reveal gate.

**Out of scope:** restoring a rejected card; any surface reporting rejections or noticing an
abandoned delivery; reconciling a dead-lettered envelope; the rejection record as a fallback
filter at sitting-open; editing a card during review; backend enforcement of the reveal gate.

## Architecture / Approach

`ReviewEvent.grade` widens into `outcome: Grade | Rejected`. Everything that must not see a
rejection keeps a `Grade` parameter, so a type error — not a convention — stops one reaching
the scheduler, and `RejectCardCommand` takes no `Scheduler` at all. The command writes the
review event and a `card_rejected` envelope in one unit of work; `OutboxWorker` claims it and
`CardDiscardHandler` delegates to `DiscardCardCommand`, which stamps `user_audit`. The
catalog already excludes discarded cards, so AC-17 falls out of the discard landing.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Rejection outcome stubs | The union type, the envelope, the renamed field | 21 construction sites across 17 files must move in one pass |
| 2. Rejection settles a card | A rejected card is done for the sitting and absent from replay | Getting `_showing_count` semantics right — a rejection is still a showing |
| 3. Rejection write-path stubs | Unit-of-work outbox, command, route, composition seams | Remember's unit of work gains an outbox it never had |
| 4. Reject command behaviour | Guard parity and the atomic pair of writes | Silently touching `scheduling_states` |
| 5. Distill discard stubs | `CardRepository.get`, discard command, handler, wiring | — |
| 6. Distill discard behaviour | The stamp and three redelivery branches | Overwriting a machine-made discard |
| 7. Acceptance for AC-17 and AC-23 | Markers, US-09 feature, steps, round trip | Steps must be appended to `remember_review.py` or coverage fails |
| 8. TUI client, store and binding stubs | `rejectCard`, `currentCard`, store action, key binding | Six `vi.mock` factories must all learn the new exports |
| 9. Reject client and store behaviour | 204 handling, re-read, due push, expiry recovery | The 204 branch must precede the `!data` guard |
| 10. Overlay gesture behind the gate | Reject only once the back is revealed | — |

**Prerequisites:** S-01 (archived). The closed `frame.md` in this folder.
**Estimated effort:** 10 phases; 1 and 8 are the widest edits, 2, 4, 6, 9 and 10 carry tests.

## Open Risks & Assumptions

- An abandoned envelope silently returns the card to circulation, and nothing notices — a
  recorded decision, not an oversight.
- The reveal gate is deliberately unenforced in the backend; a direct HTTP caller can reject
  a card it never revealed.
- The due count can briefly show a card the user has just rejected, until the discard lands.
- `pnpm generate:api` needs a running backend, so phase 8 cannot be done offline.

## Success Criteria (Summary)

- A rejected card is not drawn again in its sitting, and the sitting completes without it.
- After the outbox drains it carries a `user_audit` discard and no later sitting contains it.
- No rejection ever reaches `Scheduler.review`, in a live command or in a replay.
