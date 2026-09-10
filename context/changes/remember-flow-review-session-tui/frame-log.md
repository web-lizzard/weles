## Current State

Session closed 2026-09-10. All boundaries and requirements (FR-01..FR-06) are settled in `frame.md`'s body. One deliberately-unsettled item remains for the next stage, by design: whether the sitting overlay needs its own zustand store (mirroring `useCardsStore`/`useNotesStore`) or can extend `useAppStore` — confirmed by the user as an implementation detail, out of scope for framing; pick it up in `/discover-contracts` or `/plan`.

## Log

### 2026-09-10 — overlay-shape: new overlay via new command, distinct from browse overlay — ACCEPTED

User confirmed: this change adds a **new overlay**, entered by a **new command**, not a reuse of the notes/cards browse overlay. Grounded against `tui/src/app.tsx:1-68` and `tui/src/screens/CaptureScreen.tsx:14-72`, which show the existing `/notes` command opening `NoteListOverlay` as an absolute-positioned layer over `CaptureScreen`, toggled by a global `Escape` handler in `app.tsx`. The review overlay follows the same structural pattern (new command string, new overlay state, own screen stack), not a mode grafted onto the existing note/card browse state machine. Written into `frame.md` Boundaries and FR-01.

### 2026-09-10 — card-detail-reuse: tui-card-detail-review is unrelated — REJECTED

Considered whether `tui-card-detail-review` (visual rework of `CardDetailScreen`: front as prompt, back as check shown separately, anchor as confirmation) should share a component/gesture with this change's card-presentation step, since both separate front from back. User: that change is purely visual polish on the free-browsing distill view, with no review process attached — independent of this change. No shared contract adopted. Written into `frame.md` Boundaries as explicitly out of scope.

### 2026-09-10 — queue-visibility: progress indicator deferred to later slice — PARKED

`current-card` (`backend/src/application/remember/queries/current_card.py`) returns only the single next draw, no remaining-count. User: a progress indicator (e.g. "3/12") is not part of this change — expected to land in a later `remember-flow` roadmap slice. Parked rather than rejected, since it's a real anticipated need, just not this change's. Written into `frame.md` Boundaries as out of scope.

### 2026-09-10 — grading-gesture: two input handlers side by side, not alternatives — ACCEPTED

Initially misread by this session as an either/or choice (arrow up/down vs. number keys `1`-`4`). User corrected: both are handlers that coexist — arrow up/down moves a selection then confirms, number keys `1`-`4` grade immediately — not a toggle between two designs. Written into FR-04 as two simultaneous input paths to the same grade submission. Supersedes the earlier framing of this idea-id as an open "pick one" choice.

### 2026-09-10 — sitting-naming: "sitting" over "review" for the overlay/command — ACCEPTED

User pushed back on "review" (reads as evaluation/grading) in favor of "sitting" (reads as a study session). Grounded: the domain aggregate is already named `Sitting` (`backend/src/domain/remember/sitting.py`), and the HTTP resource is `/review-sittings` — "sitting" is the ubiquitous-language term already in use one layer down, "review" was this session's own scaffolding word, not a term from the codebase. Adopted "sitting overlay" / "sitting command" throughout `frame.md`; the literal command string is left open (see Current State). The backend route name (`/review-sittings`) is unaffected — out of scope for this change.

### 2026-09-10 — domain-error-handling: handle mid-sitting domain errors now, not later — ACCEPTED

User: handle domain errors immediately rather than deferring. Grounded the concrete error set against `backend/src/domain/remember/exceptions.py`: `EmptySittingError`, `InvalidShowingLimitError` (open-time only), `SittingNotFoundError`, `CardNotInSittingError`, `CardNotPresentableError`, `SittingAlreadyCompleteError`, `CardNotReviewableError` — each mapped to an HTTP status by `backend/src/adapters/http/errors.py`'s code table per `context/foundation/rules/exceptions.md`. Written as FR-06: any mapped domain error during the sitting flow surfaces as a visible message, never a silent failure or a stale card.

### 2026-09-10 — command-string: `/remember` over `/sitting` — ACCEPTED

User proposed `/remember` for the literal command string over the session's earlier placeholder `/sitting`. Grounded against `tui/src/screens/CaptureScreen.tsx:14-15`: `/notes` names the pillar/area (notes), not the specific screen or aggregate underneath it (`NoteListOverlay`, `CardListScreen`). `/remember` follows that same convention — it names the `remember` pillar (`origin: remember-pillar` on the parent `remember-flow-review-session` change) as the command surface, leaving room for other `remember`-pillar commands later (e.g. stats, scheduling settings) without a naming collision. Domain term "sitting" stays as the overlay/aggregate name inside `frame.md`'s body; only the literal typed command becomes `/remember`. Written into FR-01.
