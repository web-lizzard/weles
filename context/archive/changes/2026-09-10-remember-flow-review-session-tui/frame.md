---
status: closed
created: 2026-09-10
updated: 2026-09-10
---

## Boundaries

- In scope: a new **sitting overlay**, entered via a new slash-style command typed into the capture input (mirroring the existing `/notes` → `NoteListOverlay` pattern in `tui/src/screens/CaptureScreen.tsx` and `tui/src/app.tsx`), stacked the same absolute-position way over `CaptureScreen`. Named after the domain aggregate (`Sitting`, `domain/remember/sitting.py`) rather than "review" — "review" reads as evaluation/grading, while the domain and the user's mental model is a study sitting.
- In scope: driving the existing `remember` HTTP surface end to end — open a sitting, present the current card's front, reveal its back on demand, submit one of the four grades (`forgot`/`hard`/`good`/`easy`), advance to the next card, and recognize sitting completion.
- In scope: a "nothing due" state when opening the overlay finds no due cards (`NothingDueDTO`).
- In scope: surfacing the domain errors the sitting endpoints can raise mid-sitting (`SittingNotFoundError`, `CardNotInSittingError`, `CardNotPresentableError`, `SittingAlreadyCompleteError`, `CardNotReviewableError` — `backend/src/domain/remember/exceptions.py`) as a visible error state in the overlay, not a silent failure or crash.
- Out of scope: any visible queue size / progress indicator (e.g. "3/12") — the backend's `current-card` query exposes only the single next draw, no count. Surfacing that is left to a later `remember-flow` roadmap slice.
- Out of scope: reusing or coordinating with `tui-card-detail-review` — that change is a visual-only rework of `CardDetailScreen` inside the free-browsing distill/capture view (front/back/anchor separation for reading, no grading, no sitting). Confirmed independent; no shared component contract between the two changes.
- Out of scope: resuming a sitting across overlay close/reopen — `OpenSittingCommand` always opens a fresh sitting over whatever is due `as_of` now; the TUI does not need session-resume state of its own.

## Requirements

- FR-01: Typing `/remember` in the capture input opens a sitting overlay the same way `/notes` opens the notes overlay (absolute-positioned over `CaptureScreen`, dismissible, consistent with the app's existing overlay convention in `app.tsx`).
- FR-02: Opening the overlay calls `POST /review-sittings`; when the response is `NothingDueDTO`, the overlay shows a "nothing due" state instead of a card.
- FR-03: When a sitting is open, the overlay shows the current card's front only; the back is not shown until the user explicitly reveals it (`GET /review-sittings/{id}/cards/{id}/back`).
- FR-04: After revealing the back, the user can submit exactly one of the four grades (`forgot`/`hard`/`good`/`easy`) via `POST /review-sittings/{id}/cards/{id}/grade`, and the overlay advances to the next presented card from the response. Two independent input handlers both grade directly, side by side rather than as alternatives to toggle between: arrow up/down moves a selection among the four grades before confirming, and number keys `1`-`4` grade immediately.
- FR-05: When grading (or the initial open) reports `sitting_complete: true` with no further card, the overlay shows a completion state rather than attempting to present another card.
- FR-06: When any sitting-flow request fails with a mapped domain error, the overlay shows that failure as a visible message rather than leaving the user on a stale card or crashing.
