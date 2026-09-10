# Due Count — Plan Brief

> Full plan: `plan.md`

## What & Why

Users cannot learn how many cards are waiting without opening a review, and opening one
mints a sitting — exactly what AC-14 forbids. This change adds a read-only reading of the
due set: one total, broken down by why each card is waiting, visible in a shell row that
survives an open overlay.

## Starting Point

`due_card_ids` / `card_is_due` are pure and already in the domain, but their only caller
writes. The TUI has no global chrome — `CaptureScreen` owns everything above the input,
and both overlays cover it completely.

## Desired End State

A count row sits at the top of the TUI in every view, including a live review. Inside the
review overlay the same total appears with its breakdown underneath. Every number visible
at one moment comes from one computation, so no two can disagree.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where the arithmetic lives | Pure module function `partition_due`, beside `due_card_ids` | It needs the schedule and the sitting together, so it belongs to neither alone. | Frame |
| Breakdown axis | Why a card is waiting: not yet seen · seen and still owed · ripe but outside the sitting | Grade would put finished cards inside a decomposition of a waiting number. | Frame |
| Total vs breakdown | Breakdown sits inside the total, never beside it | No arithmetic a user performs on the display can produce a wrong result. | Frame |
| Response shape | Nested `due` object on all three remember DTOs | The partition is one thing; no response can carry half its buckets. | Plan |
| Query dependencies | Ports injected directly, following `CurrentCardQuery` | The signature itself says read-only; the accepted cost is four reads without a shared lock. | Plan |
| Refresh mechanism | Interval polling, 15 s, dedicated `dueStore` | The exact precedent already runs in `notesStore`; the backend needs no new infrastructure. | Plan |
| Reconciliation | One store; sitting responses push their `due` into it | Directly realizes the boundary — one computation feeds every visible number. | Plan |
| Counter home | Reserved row in `app.tsx`, above both overlays | The `WelesBrand` slot is evicted first as a conversation fills, exactly when the number matters most. | Plan |
| Error behaviour | Keep the last number, dimmed | A single dropped tick must not make the count blink out and back. | Plan |
| Acceptance layer position | Phase 4, after the stubs | Remember steps import application symbols directly, so writing them earlier means rewriting them. | Plan |

## Scope

**In scope:** the domain partition function; a read-only `DueCountQuery` and
`GET /due-cards/count`; the partition on `open`, `grade` and `current-card` responses; the
TUI due store with polling; the shell row and the overlay geometry that makes space for
it; the breakdown inside the review overlay.

**Out of scope:** any write on this path; changing `FINISHING_GRADES`, `showing_limit`, or
the scheduler; any notion of due other than `card_is_due`; the post-capture prompt (S-07)
and review entry from capture (S-06); card rejection (S-04) and source jump (S-05); a
`stories.md` v3.

## Architecture / Approach

`partition_due(live_ids, states, sitting, sitting_events, as_of, stamp) -> DuePartition`
is the single owner of the arithmetic. Over the set `due ∪ outstanding`, two booleans
decide the bucket — is the card outstanding, and has it been shown in this sitting — with
the no-sitting case branching early to put the whole total in `not_yet_seen`. Every
remember response carries the result as a nested `due` object. On the client, `dueStore`
is the only holder: polling writes to it, and sitting responses push into it, so the
header and the overlay read the same value.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Due partition stubs | `DuePartition` and the `partition_due` signature | — |
| 2. Due partition behaviour | The arithmetic, disjointness and the sum invariant | Bucketing a card that is outstanding but no longer due |
| 3. DTO, query, route and composition stubs | Every symbol the later phases import | Growing three shipped DTOs without breaking the generated client |
| 4. Acceptance layer for AC-14/AC-15 | US-07 feature and steps, red | Expressing AC-15 without a TUI in the loop |
| 5. Query and route behaviour | A real partition; US-07 green | A read path silently writing |
| 6. Partition on sitting responses | One computation per interaction | Touching three shipped S-01/S-02 handlers |
| 7. TUI client and store stubs | Regenerated schema, `dueStore` shape | `generate:api` needs a running backend |
| 8. Client and store behaviour | Mapping, polling, stale-on-error, reconciliation | Two update paths drifting between ticks |
| 9. Shell row and overlay geometry | The count survives an open overlay | Three existing test suites rest on the current geometry |
| 10. Overlay breakdown | Total with buckets underneath | Removing `N left`, which users know from S-01 |

**Prerequisites:** S-01 and S-02 shipped (both archived). A running backend for
`pnpm generate:api` at Phase 7.

**Estimated effort:** 10 phases; six backend, four TUI.

## Open Risks & Assumptions

- Ports injected directly means four reads without a shared lock — a grade landing between
  them can produce numbers from two instants. Accepted: the grade response carries its own
  partition and overwrites the store immediately after.
- The total's meaning shifts between `len(due)` with no sitting and `due ∪ outstanding`
  inside one. Inherited from the frame's accepted shape, not introduced here.
- Phase 4 leaves the acceptance suite red until Phase 5 — the same shape `session-resume`
  used (its Phase 1 red, Phase 3 green).
- AC-15's polling half is asserted only manually; the backend scenario covers a fresh read
  seeing a newly ripe card, not the tick that triggers it.

## Success Criteria (Summary)

- The count is readable with no sitting stored anywhere afterwards (AC-14).
- The number rises within one poll interval as cards become due, with no keystroke (AC-15).
- The header total and the overlay breakdown never disagree, in meaning or in time.
