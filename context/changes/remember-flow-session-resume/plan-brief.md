# Remember Flow Session Resume — Plan Brief

> Full plan: `plan.md`

## What & Why

A user who walks away mid-review should come back to the same sitting, silently, with the cards
it still holds outstanding — for as long as that sitting is inside its resume horizon. Past the
horizon the sitting stops being workable: opening a review mints a fresh one over what is due
now, and any stale `sitting_id` is refused. Covers AC-10 through AC-13 of `remember-flow` (S-02),
across backend and TUI.

## Starting Point

The shaping session left the resume half already in the working tree — `resume_horizon`,
`is_offered`, `outstanding`, `ResumeHorizon`, `latest()`, `SittingResumedDTO`, the HTTP union.
The expiry half does not exist at all: no `SittingExpiredError`, no `sitting_expired` mapping, no
clock on the two read handlers, no settings field. That gap is deliberate — shaping parked
`by-id-after-expiry` for this plan by name.

## Desired End State

`POST /review-sittings` returns an offered, unfinished sitting as `resumed` without writing
anything; the TUI shows the user they are returning and how many cards remain. Past the horizon
the same gesture mints a fresh sitting that re-collects the cards left ungraded, while grade,
current-card and reveal-back on the stale id all return `409 sitting_expired`. The TUI treats
that one code as a recovery signal, opening a fresh sitting and saying so once.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Work by id past the horizon | Refuse all three handlers with `409 sitting_expired` | One invariant covering grade, current-card and reveal-back, so an expired sitting never hands back work that cannot be completed. | Plan |
| Who recovers from expiry | The client, by calling open | Server-side auto-mint would make `POST .../grade` create an aggregate as a side effect and break `OpenSittingCommand` as sole writer. | Plan |
| TUI reaction to `sitting_expired` | Auto re-open plus a one-shot notice | The only sensible answer is a fresh sitting, but the grade the user pressed is genuinely lost, so it cannot be silent. | Plan |
| `expires_in` on DTOs | Not in this slice | The 409 is authoritative without clock agreement; `expires_at` stays a pure derivation, so nothing is foreclosed. | Plan |
| `sitting_id` in the URL | Stays | It is the axis a future grade-per-topic branches on, so removing it now means reintroducing it later. | Plan |
| Horizon configuration | `sitting_resume_horizon_hours: float = 24.0` | Matches the file's unit-in-the-name convention and keeps a sub-day horizon reachable without a type change. | Plan |
| Dead `due_card_ids` | Adopted by `OpenSittingCommand` | Mint becomes reachable twice, so the duplicated due rule is worth closing before S-03 adds a third. | Plan |
| Sitting freezes its membership | Unchanged | Expiry is the only valve through which newly-due cards enter a review. | Frame |
| Close command / stored close stamp | None | Finish stays derived from the event log; open remains the sole writer. | Contracts |

## Scope

**In scope:** convergent open returning a resumed sitting; the horizon as a configured value; a
409 refusal on all three by-id handlers; acceptance scenarios for AC-10…AC-13; TUI resume marker,
live outstanding count, and expiry recovery.

**Out of scope:** `expires_in`/`expires_at` on DTOs; any URL-shape change; a "start fresh" mode;
a close command; the due count (S-03); ownership or authentication; a SQL adapter.

## Architecture / Approach

```
POST /review-sittings ──▶ OpenSittingCommand.handle
                              │
              ┌───────────────┴────────────────┐
        latest() offered                 else mint
        and unfinished                due_card_ids(...)
              │                              │
      SittingResumedDTO              SittingOpenedDTO / NothingDueDTO
              │                              │
              └──────────┬───────────────────┘
                         ▼
              tui store/sitting.ts  ──(409 sitting_expired)──▶ re-open + notice
                         │
                 SittingOverlay.tsx  ── "Resumed" (one-shot) + "N left" (persistent)
```

Acceptance layer first, then backend settings → convergent open → expiry guard, then the TUI
bottom-up (API client → store → screen).

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Acceptance layer | Scenarios for AC-10…AC-13, advanceable `_FixedClock`, horizon seam on the test composition | The clock change touches a fixture every remember scenario shares |
| 2. Settings & compose | `sitting_resume_horizon_hours`, `ResumeHorizon` built at the edge | A zero or negative value fails at import rather than at request time |
| 3. Convergent open | Resume branch in `handle()`; `due_card_ids` adopted | Rewrites a body S-01 scenarios depend on |
| 4. Expiry stubs | `SittingExpiredError`, 409 mapping, `Clock` on both read handlers | Constructor change ripples to every construction site |
| 5. Expiry guards | The three refusals | Guard order in `_guard_grade` must precede any write |
| 6. TUI API stubs | Regenerated schema, `ResumedSitting`, `SITTING_EXPIRED` | Regeneration needs a running backend — manual |
| 7. TUI API behaviour | `resumed` and `outstanding_count` mapped | Existing code throws on any non-`opened` kind |
| 8. TUI store stubs | `isResumed`, `outstandingCount`, `notice` | Widened shape touches the shared `resetStore` helper |
| 9. TUI store behaviour | Marker, live count, expiry recovery | Recovery must not loop when the re-open itself fails |
| 10. Overlay render | "Resumed", the count, the notice | — |

**Prerequisites:** S-01 (`remember-flow-review-session`) and its TUI change, both archived.

**Estimated effort:** 10 phases; the backend half (1-5) is the substantive one, the TUI half
(6-10) is thin per phase but spans four files.

## Open Risks & Assumptions

- The resume marker's form — one-shot "Resumed" plus a persistent count — was assumed at the
  phase-approval gate rather than asked; the frame requires both facts but not this shape.
- `pnpm generate:api` needs a live backend, so Phase 6 cannot complete unattended.
- Expiry recovery discards the grade the user just pressed. This is consistent with AC-13
  (grades *already given* keep counting) but is a real, visible loss the notice must own.
- `SITTING_RESUME_HORIZON_HOURS` doubles as the manual-testing lever; a very small value is the
  only practical way to cross the horizon by hand.

## Success Criteria (Summary)

- `cd backend && uv run pytest` green, including `tests/bdd -m "remember-flow"` with the four new
  AC tags
- `cd tui && pnpm test && pnpm typecheck && pnpm lint` clean
- Manually: `/remember` → grade → ESC → `/remember` returns the same sitting marked resumed with a
  lower count; past the horizon it recovers into a fresh sitting instead of erroring
