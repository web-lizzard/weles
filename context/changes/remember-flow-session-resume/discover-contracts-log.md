## Current State

Session **closed** 2026-09-10 on `remember-flow-session-resume`. Frame closed. Live S-01 handler bodies kept; convergent resume is documented on `OpenSittingCommand.handle` until `/implement` / `/plan`.

**Sitting** is write-once. No `closed_at`, no stored `expires_at`. Finish and outstanding are derived from the event log + live catalog. Horizon is `resume_horizon` (VO) snapshotted at open like `showing_limit`. `is_offered(as_of)` is `as_of < opened_at + resume_horizon.value`. Resumable iff offered and not finished.

**ResumeHorizon** must be strictly positive. One day is `MIN_RESUME_HORIZON`, the planned Settings default — `/plan` wires Settings + compose. Not a type floor.

**Lookup:** `SittingRepository.latest()` (greatest `opened_at`). Application evaluates offer and finish. Uniqueness is the mint guard on convergent open, not a list.

**OpenSittingCommand** is the only re-entry. No close command. Same `handle()`: resume `SittingResumedDTO` or mint `SittingOpenedDTO` / `NothingDueDTO`. `kind=resumed` plus `outstanding_count` mark a return; sitting id is not user-facing.

**Dropped:** `ResumableSittingQuery` (no GET peek in this slice). `DueCountQuery` (S-03). Stored close stamp.

**Parked for `/plan`:** Settings default for the horizon; whether grade / current-card by id still work after the horizon; HTTP union; in-memory `latest()`; filling the convergent open body; TUI `kind` + count.

## Log

### 2026-09-10 — session-open: domain and application draft — OPEN

First write of the pair. Frame is `status: closed`. User asked to start with domain/application and to shape three frame leftovers: POST vs GET for the current sitting, a close date so sittings can be closed, and where the overdue count is computed and returned.

**Why:** Closed-frame gate passed. No prior `discover-contracts.md`. Adapters and HTTP deferred on purpose so the user can size the next instruction.

### 2026-09-10 — close-date-vs-expiry: snapshot expires_at; no later close column — OPEN

Drafted `expires_at` on `Sitting` at open. Did not add `closed_at` / `close_date`.

**Why:** S-01 already made the sitting write-once (`OpenSittingCommand` is the only writer; grade writes events and scheduling state). A close stamp set on finish or on expiry is a second copy of a derivable fact (finished from the log, expired from `opened_at` + horizon) and would force a second save of the aggregate — from grade, from open, or from an explicit close command. Explicit close is also the start-fresh / abandon mode the frame put out of scope. What *does* need storing at open is the horizon itself, because like `showing_limit` it must outlive a later settings change. That instant is `expires_at`, not a close date.

**Consequence:** "Closing" a sitting stays derived: finished or past `expires_at`. Lookup is not a `closed_at IS NULL` column filter.

### 2026-09-10 — repo-vs-app: list_unexpired, application evaluates finish — ACCEPTED

`SittingRepository` gains `list_unexpired(as_of)`. Finish and outstanding stay on the aggregate and are evaluated in application glue after loading events and the live catalog.

**Why:** Frame leftover: done-ness cannot be a plain column filter. Horizon can, once `expires_at` is on the row. Splitting the two keeps the port honest for a later SQL adapter without making the repository reconstruct membership.

### 2026-09-10 — convergent-open: lookup lives inside OpenSittingCommand — ACCEPTED

`OpenSittingCommand.handle` is rewritten as orchestration `...`: unexpired candidates → not finished → at most one → resume DTO; else existing due-set open.

**Why:** Already accepted on the frame (`resume-lookup`). Written now so the command, not a stored pointer and not the client, is the uniqueness guard and the silent return.

### 2026-09-10 — get-current-sitting: ResumableSittingQuery drafted, HTTP parked — OPEN

A read-only `ResumableSittingQuery` mirrors the lookup half of open and returns `SittingResumedDTO | None`. No route written.

**Why:** A GET next to POST is only a different *verb* if someone must observe without creating. Convergent POST already finds the sitting when `/remember` is the gesture. The query is on disk so the user can keep or drop it before HTTP is shaped. Frame still says S-03's due count is the consumer that must ask without acting — and that consumer is a different query (`DueCountQuery`), not "GET current sitting".

### 2026-09-10 — outstanding-on-dto: count is sitting.outstanding, on the presented DTOs — ACCEPTED

`Sitting.outstanding` plus `outstanding_count` on `PresentedCardDTO` / `GradeAppliedDTO`. Resume is marked with `SittingResumedDTO.kind = "resumed"`.

**Why:** Frame `silent-versus-invisible`: the return is marked and counted; the id is not a user-facing fact. The sitting already knew unfinished members internally; the DTO did not. Lowest-grade cards stay outstanding, so the number is unfinished members, not grades performed.

### 2026-09-10 — due-count-query: S-03 surface drafted, not this slice — PARKED

`due_card_ids` + `DueCountQuery` + `DueCountDTO` written as signatures. Not part of open/resume. Not returned as a substitute for outstanding.

**Why:** AC-14/AC-15 are out of this frame. The overdue number is cards due *now* against scheduling state (`card_is_due`), independent of any sitting. Putting it only on POST open would start a sitting to learn the number. Sharing `due_card_ids` with open avoids a second due definition later. Parked as work for `remember-flow-due-count`; left visible so the user can estimate S-03 from a real shape.

### 2026-09-10 — resume-horizon-vo: duration VO with a one-day floor — OPEN

`ResumeHorizon` stays a VO. Floor raised from strictly positive to `>= timedelta(days=1)` (`MIN_RESUME_HORIZON`). The VO is not stored on `Sitting`; minting still writes `expires_at`.

**Why it is a VO:** same job as `ShowingLimit` — compose wraps a setting once, the command must not see raw env, the type refuses illegal durations. It names how long a *new* sitting stays offered.

**Why the floor is written but not yet accepted:** `ShowingLimit >= 1` is structural (N=0 finishes every card without showing). A 12-hour horizon still implements AC-12. The frame's "lifetime measured in hours, not view mounts" argues against minutes, not against half a day. A day was the PRD's assumed *default*, and putting that number on the type means settings can only lengthen. Tests of expiry then always advance the clock by at least a day (fine with a fake clock). Direct `Sitting(..., expires_at=...)` can still mint a shorter window; the floor is enforced at compose→command, not on the row.

**Consequence:** confirm whether a day is the smallest *meaningful resume*, or only the default while the VO keeps "positive" (or a smaller floor such as one hour).

### 2026-09-10 — repo-vs-app: list_unexpired dropped for list() — ACCEPTED

`SittingRepository.list_unexpired` is gone. Port is `list()`. Open and the peek query filter with `sitting.is_offered(as_of)` then `is_finished`.

**Why:** Unexpired on the port was an index leaking into the contract. `is_offered` already owns `expires_at > as_of`. The method still could not return "the resumable sitting": a sitting finished this morning stays unexpired until the horizon, so the list was never the answer, only a smaller haystack. There is no stored pointer (frame `resume-lookup`), so a scan exists — but it is a dump, not a policy query. A later SQL adapter may index `expires_at` inside `list()` without naming that in the port.

**Supersedes:** the 2026-09-10 `repo-vs-app` entry that accepted `list_unexpired`.

### 2026-09-10 — repo-vs-app: latest not list — ACCEPTED

`SittingRepository.list` is gone. Port is `latest() -> Sitting | None` (greatest `opened_at`). Open/peek evaluate offer and finish on that one row.

**Why:** Uniqueness is a mint rule, not a query that returns a set. While a sitting is resumable we never save another, so an older row cannot still be the one to offer back. `latest` is not "the resumable sitting" — a finished or expired latest means there is none, and we mint. The repository still does not know finish. A uniqueness bug (two offered unfinished) would hide behind `latest`; that was already a mechanism without its own AC.

**Supersedes:** the 2026-09-10 `repo-vs-app` entry that accepted `list()`.

### 2026-09-10 — due-count-query: not this change — REJECTED

`DueCountQuery` and `DueCountDTO` deleted. `due_card_ids` stays as the mint path's due set for `OpenSittingCommand`. Outstanding-in-sitting is unchanged.

**Why:** User: we are not doing S-03. AC-14/AC-15 are out of the frame; a query that only exists to size the next slice is contract noise. S-03 can mint its own query against `card_is_due` / `due_card_ids` later.

**Supersedes:** the 2026-09-10 `due-count-query` PARKED entry.

### 2026-09-10 — open-flow: one command, no close, resume until expiry or finish — ACCEPTED

User's walkthrough, with two corrections, is the contract: first successful open mints a sitting over due cards; work is grade/reveal on that sitting; coming back is the same command, which returns that sitting while it is offered and unfinished.

**Why the corrections hold:** There is no close gesture — frame forbade start-fresh and stored close; leaving is the client going away. Resume is not "until expiry" alone: a finished sitting, even inside the horizon, is not offered back (latest is finished → mint or nothing_due). Expiry without finish also mints over whatever is due now, including ungraded cards from the expired batch.

### 2026-09-10 — horizon-on-sitting: ResumeHorizon field, expires_at gone — ACCEPTED

Sitting stores `resume_horizon` like `showing_limit`. `expires_at` is not a field. `is_offered` derives `opened_at + resume_horizon.value`. `InvalidSittingExpiryError` removed.

**Why:** Bare `expires_at` existed to feed `list_unexpired`, which we dropped. After that it was `opened_at` plus the duration stored twice, with a guard that only refused inverted clocks. The thing that must outlive env is the policy VO — same reason `showing_limit` is on the row. A later store may persist a generated instant without the domain naming it.

**Supersedes:** the stored-instant half of `close-date-vs-expiry` and the "VO is not a field" half of `resume-horizon-vo`.

### 2026-09-10 — contract-no-bodies: restore live handlers, comment the slice — ACCEPTED

User: do not delete working code; leave the new flow as comments. Restored `CurrentCardQuery.handle`, `OpenSittingCommand.handle` (mint-only), `GradeCardCommand._applied_dto`. `outstanding` / `is_offered` / `due_card_ids` filled so those handlers can call them. Convergent open stays in the open-sitting docstring. `ResumableSittingQuery` remains unwired.

### 2026-09-10 — remaining-surface: three contract questions, rest is implement — OPEN

Asked what is left to model. Domain/application for AC-10–13 is shaped: write-once sitting, `resume_horizon` VO, `latest` + `is_offered`/`is_finished`, convergent open, outstanding on DTOs, no close, no due-count query.

**Why three leftovers are still model, not `/plan`:** GET peek has no AC in this slice; the one-day floor vs default changes what the VO refuses; by-id after expiry is an invariant on existing commands the frame never named. HTTP, Settings, `latest()` adapter, and filling the open body are implementation of decisions already written.

### 2026-09-10 — get-current-sitting: no peek query in this slice — REJECTED

Deleted `ResumableSittingQuery`. Resume is convergent `OpenSittingCommand` only.

**Why:** User: remove the query. AC-10–13 have no consumer that must ask without creating. S-03 is a different query later.

**Supersedes:** the 2026-09-10 `get-current-sitting` OPEN entry.

### 2026-09-10 — resume-horizon-vo: one day is Settings default, not a type floor — ACCEPTED

VO stays strictly positive. `MIN_RESUME_HORIZON` (`timedelta(days=1)`) is the planned Settings default. `/plan` wires Settings and compose. OpenSittingCommand may keep the constant as a fallback until then.

**Why:** User: default in settings, log it, do it in plan. A day is configuration (PRD open question), not an invariant like `ShowingLimit >= 1`.

**Supersedes:** the 2026-09-10 `resume-horizon-vo` OPEN entry that put the floor on the type.

### 2026-09-10 — by-id-after-expiry: plan decides whether id handlers refuse after horizon — PARKED

Grade and current-card by `sitting_id` after `is_offered` is false is a `/plan` question, not a contract to close here.

**Why:** User: already a plan decision. Session can close.

### 2026-09-10 — remaining-surface: session closed — ACCEPTED

User closed: drop the query, horizon default in Settings via plan, by-id-after-expiry in plan.

**Supersedes:** the 2026-09-10 `remaining-surface` OPEN entry.







