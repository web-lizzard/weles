# Remember Flow Review Session TUI — Plan Brief

> Full plan: `plan.md`

## What & Why

Add a sitting overlay to the TUI so a user can review due cards without leaving the terminal.
Typing `/remember` drives the already-implemented `remember` backend end to end: open a
sitting, show a card, toggle its back, grade it, and advance — mirroring the existing `/notes`
overlay's shell pattern.

## Starting Point

The backend (`remember-flow-review-session`) is implemented and green: three HTTP endpoints
(open, reveal back, grade) exist and are stable. The TUI has none of the client-side pieces yet
— no API module, no store, no screen — and its generated OpenAPI schema predates these routes.

## Desired End State

`/remember` opens an overlay that opens a sitting, shows the current card's front, toggles the
back on and off with `t` at any time, grades with a number key or arrows+Enter regardless of
whether the back is showing, advances card to card, and lands on a nothing-due, complete, or
retryable-error state. ESC closes it from anywhere.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Grade confirm | Enter confirms an arrow-highlighted grade; number keys grade immediately | Matches FR-04's "before confirming" wording and avoids an arrow-overshoot misgrading | Question |
| Error recovery | In-place retry, re-issuing the exact failed action | Faster recovery than forcing a full overlay reopen | Question |
| Loading feedback | Show a loading indicator during in-flight requests | Consistent with `NoteListOverlay`'s existing convention | Question |
| Nothing-due UX | Message + ESC only, no extra affordance | Matches the minimal existing overlay convention; frame excludes queue counts | Question |
| Reveal key | `t` toggles front/back, not Enter | Enter is already the grade-confirm key on the same view; a dedicated key avoids overload | Question |
| Toggle scope | Full toggle (`t` flips back on and off any number of times) | User's explicit choice — lets a reader glance back at the front before grading | Question |
| Grading vs. toggle | Grading (`1`-`4`, arrows+Enter) works regardless of `isBackVisible` | User's explicit correction — the toggle is a pure display flag, never a gate on grading | Question |

## Scope

**In scope:** `api/sittings.ts`, `store/sitting.ts`, `screens/SittingOverlay.tsx`, and the
`/remember` wiring into `CaptureScreen.tsx`/`app.tsx`/`store/index.ts`.

**Out of scope:** any backend change, the `current-card` query (unused — open/grade responses
already carry the current card), resume-across-reopen, queue-size display, and
`tui-card-detail-review` (confirmed independent).

## Architecture / Approach

Bottom-up: API client → store → overlay screen → app-shell wiring, each layer depending only on
the one below it. The first three are TDD'able and get a stubs phase before behaviour, per this
repo's stubs-then-behaviour convention (no closed `discover-contracts.md` exists for this
change). The overlay's behaviour is split into a happy-path phase and a terminal/edge-states
phase to keep each phase's test count within this repo's TUI convention (1-5 tests/phase).

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. API client stubs | Schema regen + `api/sittings.ts` signatures | Schema regen needs a running backend — easy to skip by accident |
| 2. API client behaviour | Fill `openSitting`/`revealBack`/`gradeCard`, error mapping | Distinguishing `OpenedSitting` vs `NothingDue` by `kind` |
| 3. Sitting store stubs | `store/sitting.ts` state/action signatures | Getting the state shape right before behaviour locks it in |
| 4. Sitting store behaviour | Full state-machine transitions incl. retry | Retry must re-issue the *exact* failed action, not just re-open |
| 5. Overlay stubs | `SittingOverlay.tsx` component signature | — |
| 6. Overlay happy path | Loading/front/toggle/both grade paths/advance | Grade keys must stay live regardless of `isBackVisible` |
| 7. Overlay terminal states | Nothing-due/complete/error+retry rendering | Error retry keypress must not collide with grade digit keys |
| 8. Wire `/remember` | Command, shell flag, absolute mount, ESC | Overlay must disable capture-input focus like `/notes` does |

**Prerequisites:** none beyond the frame being closed (it is) and the backend routes being live
(they are).

**Estimated effort:** medium — eight phases, three new files, three small edits to existing ones.

## Open Risks & Assumptions

- `PresentedCardDTO`'s `card_id`/`front` going nullable is an uncommitted backend change at
  plan time; this plan is written against that shape since it is what FR-05 requires.
- `pnpm generate:api` requires a running backend at plan/implementation time — a one-line manual
  step easy to forget, called out explicitly in Phase 1.

## Success Criteria (Summary)

- `cd tui && pnpm test`, `pnpm typecheck`, and `pnpm lint` all green.
- A full sitting (open → grade every card → complete, and separately → nothing-due) worked
  through manually against the live backend.
