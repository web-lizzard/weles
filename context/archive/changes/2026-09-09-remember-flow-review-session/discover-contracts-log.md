## Current State

Session **closed** on `remember-flow-review-session`. Frame closed. HTTP, compose, and adapters unwritten. Signatures only — no method bodies.

**Sitting** is the write-once aggregate: `id`, `card_ids`, `opened_at`, `showing_limit` (snapshotted at open, persisted with the row). Events are never a field. Application loads `list_by_sitting` and passes events in. Public: `contains`, `visible`, `next_card`, `is_finished`. `_eligible_pool` is private. Grade: `is_finished` then `card_id == next_card`. `ReviewEvent` does not import `Sitting`.

**SittingCompletion** is the named completion helper used inside Sitting. **SittingOrder is gone.** `sitting_seeded_draw` is the pick `next_card` calls. Compose does not inject `Draw`.

**Ports:** UoW owns `sittings`, `review_events`, `scheduling_states`. Outside UoW: `ReviewCatalog`, `Scheduler`, `Clock`. Queries never receive a UoW.

**Client loop:** Open (first front) → Reveal(`card_id`) → Grade(`card_id`) → next front on `GradeAppliedDTO` or complete. `CurrentCardQuery` is reread by `sitting_id`. Reveal is sittings + catalog only. Compose injects `ShowingLimit` only into `OpenSittingCommand`.

**SchedulerStamp:** `SchedulerAlgorithm.FSRS` + `parameter_version` str. **OpaqueSchedulerState.payload:** `dict[str, object]`; domain does not index keys. UTC is `Clock.now()`; no `NonUtcTimestampError` / `require_utc`.

Still unresolved (for `/plan`): remember vs distill `CardId`; `due_at <= as_of`; default `sitting_max_showings=2`; `parameter_version` as closed pin vs string; foreign-sitting events on Sitting; HTTP; `InvalidShowingLimitError` as a mapped CoreException.

## Log

### 2026-09-09 — session-open: first contract draft, backend domain and application — OPEN

**Why:** User invoked `/discover-contracts remember-flow-review-session` and asked for a signature draft focused on backend and domain. Frame is closed (`status: closed`). No prior `discover-contracts.md`. HTTP, adapters, and method bodies are out of this turn on purpose.

### 2026-09-09 — hex-layout: remember mirrors distill/capture layering — ACCEPTED

**Why:** Forced by `context/adrs/hexagonal-arch-shape` and the live tree: domain ports in `domain/remember/ports.py`, application `UnitOfWork` in `application/remember/ports.py` owning only transactional stores, commands vs queries split, DTOs as pydantic models, in-memory-first later. Scheduler is a domain service port, not a UoW member — it is CPU, not a commit participant. Catalog is a read port onto distill, also outside UoW.

### 2026-09-09 — remember-card-id: remember-owned CardId, not distill's — OPEN

**Why:** Duck said remember's domain never learns distill's model and is keyed by card id. Distill already has `domain.distill.value_objects.CardId`. Sharing that type is one identity for one card; owning a twin UUID wrapper keeps the pillar boundary and makes the catalog adapter the only mapper. Draft uses the twin. Needs a ruling before the adapter is shaped.

### 2026-09-09 — presentation-stability: seeded draw so next card is a pure function of stored facts — OPEN

**Why:** Frame forbids a stored cursor and asks for a random draw from the least-shown undone pool, with an injectable RNG for tests. A sitting spans requests (`frame-log` `session-durability`). A process-global or per-call random draw would present a different card on reveal than on open. Seeded draw from sitting id + events keeps: no cursor, no sitting mutation, test injection via `Draw`, and a stable "card in front" for `CurrentCardQuery` / `RevealBackQuery` / `GradeCardCommand`. Grade still takes `card_id` and must match that pick. Alternative: client holds the card id and the server only checks `eligible_pool` — weaker AC-04, no re-draw identity. Written as seeded; not yet accepted.

### 2026-09-09 — due-comparison: due_at <= as_of, including exactly now — OPEN

**Why:** Frame says a card belongs when it has no scheduling record or its next-due date has passed. FSRS new cards are due immediately (`research.md`). `<=` is the usual due query and matches "due at that moment" (AC-01). Strict `<` would drop cards whose `due_at` equals `as_of`. Written as `<=`; confirm.

### 2026-09-09 — scheduler-inputs: sitting id is invisible to Scheduler.review — ACCEPTED

**Why:** Frame: reconstruction never reads sitting identity; seed is derived from card, reviewed_at, grade. Passing the whole `ReviewEvent` into the scheduler would let the adapter "see" sitting id. The port takes the three replay fields only. `ReviewEvent.sitting_id` stays for sitting queries.

### 2026-09-09 — event-before-memo: grade UoW saves the event first — ACCEPTED

**Why:** Frame: of event and memoized state, the event must not be lost. In-memory UoW commits both or neither; the save order still records the asymmetry for a later real store.

### 2026-09-09 — http-surface: routes and compose wiring deferred — PARKED

**Why:** User asked to focus on backend and domain. Exception codes are mapped because `test_every_core_exception_code_is_mapped_to_a_status` walks all `CoreException` subclasses. Routers, `compose.py`, and adapters stay unwritten.

### 2026-09-09 — showing-limit-default: sitting_max_showings = 2 — OPEN

**Why:** FR-005 / AC-09 as a floor plus the frame's "shown N times": a failed card returns at least once more, so N=2 is the smallest value that keeps that promise. Environment setting alongside `card_front_max`. Confirm or pick another default.

### 2026-09-09 — sitting-behavior: no mutating methods on Sitting besides open — ACCEPTED

**Why:** User asked whether the frame gave this aggregate anything to *do* besides opening. It did not give commands. Contrast `CaptureSession` (`assign_topic`, `draft_note`, `approve`) — those exist because that session changes. Frame: the sitting record "is written once and never changed"; "how often a card has been shown, which cards are finished, … which card comes next are derived from the log and stored nowhere"; "the sitting holds no reference to its events, and neither knows the other's type"; join "lives in the application layer". `grade` / `reveal` / `next` on `Sitting` would break at least one of those. Leaving unfinished is not an error and needs no `abandon()`; expiry is S-02.

**Consequence:** `OpenSittingCommand` is the only use case that writes a `Sitting`. Grade writes events and scheduling state. Reveal is a query.

### 2026-09-09 — sitting-read-invariants: contains and visible — ACCEPTED

**Why:** The frame *did* give the aggregate two read invariants that do not need the log: membership is the stored set, and a card discarded elsewhere "drops out of it when the set is read, rather than being removed from it". Those are now `contains` and `visible(live)`. Completion and ordering stay named concepts beside the aggregate, not methods on it.

### 2026-09-09 — contract-no-bodies: signatures only, bodies are out of this session — ACCEPTED

**Why:** User called out that the session kept filling method bodies after they had already been stripped back to `...`. Discover-contracts writes the shape, not the implementation. `contains`, `visible`, `SittingCompletion.*`, `SittingOrder.*` stay as signatures. Do not restore bodies in later turns of this session.

### 2026-09-09 — named-rules-off-sitting: SittingCompletion and SittingOrder stay off Sitting — OPEN

**Why:** User asked to negotiate: separate function vs methods on the session aggregate. The files already hold two types beside `Sitting`, not free functions and not methods on `Sitting`. Recommendation is to keep that: see chat. Not accepted until the user says so.

### 2026-09-09 — named-rules-off-sitting: two types beside Sitting; the application is the glue — ACCEPTED

**Why:** User accepted leaving completion and order off the aggregate. `SittingCompletion` and `SittingOrder` remain domain types next to `Sitting`. The piece that loads a sitting, loads that sitting's events, intersects membership with the catalog via `visible`, and constructs those two types is the **application** — commands and queries. That join is the glue; it is not a method on `Sitting` and it is not an event in the log. Supersedes the OPEN entry of the same id earlier this day.

### 2026-09-09 — scheduler-vo-split: stamp readable, payload opaque, two types — ACCEPTED

**Why:** User asked what `SchedulerStamp` and `OpaqueSchedulerState` are. They are the frame's two non-`due_at` halves of per-card scheduling state (`frame.md` "What is recorded"): next-due the domain owns, an opaque value it never interprets, a stamp naming algorithm and parameter version. The split is the invariant: `GradeCardCommand` compares stamps (`handle` step 6); `Scheduler.review` is the only code allowed to mean the blob. `bytes` rather than a dict keeps the domain from naming FSRS fields. Confirmed, not rewritten.

### 2026-09-09 — stamp-vocabulary: free strings vs closed algorithm id — OPEN

**Why:** `SchedulerStamp` is two unconstrained `str`s. The domain must compare stamps and must not interpret them, so a closed enum of algorithms would already be interpretation. Free strings also mean `("", "")` is a valid stamp. Not ruled this turn.

### 2026-09-09 — stamp-vocabulary: algorithm is SchedulerAlgorithm; parameter_version stays str — ACCEPTED

**Why:** User wanted an enum on the stamp. Closed id belongs on the *algorithm* (one member now: `FSRS`), because a second algorithm is a new port implementation the domain must be able to tell apart from the first. `parameter_version` stays a string: research pins invalidation to the library/defaults bump (`fsrs` 6.3.2), which is not a domain vocabulary. Domain still does not run FSRS; it only compares stamps. Supersedes the OPEN entry of the same id earlier this day.

### 2026-09-09 — opaque-payload-dict: dict[str, object], not bytes — ACCEPTED

**Why:** User rejected bytes as a domain encoding that the adapter would unpack on every review. `Card.to_dict()` is already a mapping (`research.md`); bytes would be a persistence encoding leaking into the VO. Opacity is now a rule (do not read keys), not a type-system wall. Store serialization stays in the persistence adapter. Revises the bytes rationale in `scheduler-vo-split` the same day.

### 2026-09-09 — non-utc-core-exception: NonUtcTimestampError as a wire error — REJECTED

**Why:** User called it overengineering. Capture/distill mint `datetime.now(UTC)` and have no tz `CoreException`. Frame's UTC rule is about one captured instant handed to the scheduler, and that instant comes from `Clock.now()`, never from the client. A mapped 422 would treat a clock/adapter bug as input validation. Removed the class and `non_utc_timestamp` from the HTTP map. `require_utc` remains a construction guard raising `ValueError`.

### 2026-09-09 — require-utc-helper: domain tz guard — REJECTED

**Why:** User called `require_utc` an implementation detail. UTC is produced at the clock and consumed by the scheduler adapter; domain models store `datetime` and do not re-check tz. Deleted the helper and the tz-only validators on `ReviewEvent` and `SchedulingState`. `Sitting._validate_intent` is empty membership only. `Clock.now()` remains the named source. Supersedes the leftover `require_utc` sentence in `non-utc-core-exception` the same day.

### 2026-09-09 — reveal-thin-ctor: sittings + catalog only — ACCEPTED

**Why:** User called `RevealBackQuery`'s constructor bloated. The extra deps (`events`, `ShowingLimit`) existed only to re-run seeded `next_card` and assert `handle`'s `card_id` is the one in front — a copy of `CurrentCardQuery`. Reveal already takes `card_id`; AC-03 is "back on request", AC-04 is one card in front (the current-card query / UI), and "must match the pick" belongs on grade (`presentation-stability`). Consequence: a client can ask for another sitting member's back without it being in front. Grade still refuses a non-presentable card.

### 2026-09-09 — client-loop: open shows first card; reveal then grade; current is reread — ACCEPTED

**Why:** User restated the API as open then grade/current/reveal. Open already returns the first front (`SittingOpenedDTO`). Grade already returns the next front or complete (`GradeAppliedDTO`). The repeating pair is Reveal → Grade. `CurrentCardQuery` stays for a later request that has only `sitting_id` (sitting spans requests; resume/expiry are still out of scope).

### 2026-09-09 — showing-limit: cap on showings per card per sitting — ACCEPTED

**Why:** User asked what `ShowingLimit` is. It is the frame's configured showing count: a card finishes in this sitting when graded Good+ *or* shown this many times. Lives in settings, injected into `SittingCompletion`, never stored on `Sitting`. Default 2 (FR-005 floor) is still the OPEN `showing-limit-default`. Docstring added; `InvalidShowingLimitError` left mapped.

### 2026-09-09 — showing-limit-ctor: injected at compose, not per request — ACCEPTED

**Why:** User asked if the constructor exists so composition can inject it. Yes. Frame forbids a policy field on the sitting and a substitutable per-sitting choice. `handle` must not take N. Application must not import `Settings`. Compose wraps `sitting_max_showings` into `ShowingLimit` once, same as `CardLengthPolicy(front_max=_settings.card_front_max)` today.

### 2026-09-09 — draw-seam: pick from eligible pool; seed in prod, inject in tests — ACCEPTED

**Why:** User asked what `Draw` is. `SittingOrder` first builds the least-shown undone pool; `Draw.pick` only chooses among that pool. The ordering rule is not substitutable; the random source is (frame). Production `sitting_seeded_draw` keeps open/reveal/grade seeing the same card without a stored cursor. Unlike `ShowingLimit`, compose must not inject a process-global RNG — that would break presentation stability. Optional ctor `Draw` on Open/Grade is tests only. Docstrings added.

### 2026-09-09 — draw-domain-forced: sitting_seeded_order on live paths — ACCEPTED

**Why:** User asked whether the pick should be enforced by the domain, not optional on commands. Application handlers no longer take `Draw`. Production assembly is `sitting_seeded_order` (always `sitting_seeded_draw`). `SittingOrder` still accepts a `Draw` so unit tests of the pool/pick split can stub it. Compose cannot override the live pick. Supersedes the "optional ctor Draw on Open/Grade" sentence in `draw-seam` the same day.

### 2026-09-09 — named-rules-off-sitting: put order and draw on Sitting? — OPEN

**Why:** User asked whether `SittingOrder` and the card draw should live on the aggregate, after we forced seed in the domain. Frame still says the sitting is write-once, next-card is derived from the log, and neither type knows the other (`frame.md`). `sitting.next_card(...)` needs events to seed and to count showings, so `Sitting` would import `ReviewEvent`. A method that takes `SittingCompletion` still cannot seed without events. Recommendation: keep `sitting_seeded_order` beside `Sitting`; domain-forced draw does not require moving the rule onto the aggregate. Not moved unless the user overrides the frame.

### 2026-09-09 — named-rules-off-sitting: invariants on Sitting; events as args — ACCEPTED

**Why:** User preferred the aggregate as the place that cannot be bypassed by importing a helper, while still not storing events. `eligible_pool` / `next_card` / `is_finished` take `Sequence[ReviewEvent]` and `ShowingLimit`. No event field. Seeded draw is inside `next_card`. `SittingCompletion` and `SittingOrder` stay named types used from those methods. Application loads both sides and calls `Sitting`. Cost: `Sitting` knows `ReviewEvent`'s type (frame's "neither knows the other" is one-way now). `ReviewEvent` still does not import `Sitting`. Supersedes the same-day ACCEPTED "two types beside Sitting; application is the glue" and the OPEN "put order and draw on Sitting?".

### 2026-09-09 — sitting-query-methods: pool is now-presentable, not membership — ACCEPTED

**Why:** User restated the shape as SittingId receiving its events. It is `Sitting`, not `SittingId`. Application passes `list_by_sitting`. `eligible_pool` ≠ frozen set: it is the current-round candidates. `is_finished` walks `present` (after `visible`), not discarded members. Docstrings tightened.

### 2026-09-09 — eligible-pool-private: _eligible_pool on Sitting — ACCEPTED

**Why:** User asked whether `eligible_pool` is exposed and whether it should be private. The only application use was Grade's presentable guard. The set is an intermediate of `next_card`, not a client/API fact. Renamed `_eligible_pool`. `SittingOrder.eligible_pool` stays for tests of that type.

### 2026-09-09 — presentation-stability: grade must match next_card — ACCEPTED

**Why:** With `_eligible_pool` private, Grade cannot membership-test the pool. Guard is `card_id == sitting.next_card(...)` (after `is_finished`). Client still sends `card_id`; it must be the seeded pick. Closes seeded vs client-held on the grade path: both — client holds the id, server re-derives the pick. `is_finished` is checked first so a complete sitting is not reported as `CardNotPresentableError`.

### 2026-09-09 — sitting-order-type: SittingOrder beside Sitting — REJECTED

**Why:** User asked if `SittingOrder` is still needed now that Sitting owns the algorithm. A second public type is another import path for the same invariants. Ordering is `Sitting.next_card` / `_eligible_pool`. `SittingCompletion` stays (finished vs due_at). `sitting_seeded_order` deleted; `sitting_seeded_draw` remains the pick `next_card` calls. Frame's "named ordering concept" is the Sitting methods, not a parallel class.

### 2026-09-09 — showing-limit-not-on-wire: config VO, not a computed sitting field — ACCEPTED

**Why:** User asked if ShowingLimit is like a VO that is never presented, only computed on the aggregate. It is never on DTOs (`sitting_complete` is the derived bool). It is *not* computed: it is process config, injected, passed into Sitting methods. The aggregate computes pool/pick/finished *from* events + that N. Still a VO so `>= 1` lives in one type, same pattern as `CardLengthPolicy`.

### 2026-09-09 — showing-limit-on-sitting: freeze N at open — ACCEPTED

**Why:** User asked compose-every-call vs a frozen aggregate field. Compose already binds settings once; the leak was passing N into every handler. The log can count showings but not the threshold, so N belongs with identity/membership/`opened_at`. `Sitting.open(..., showing_limit)`. Grade/current drop `ShowingLimit` from their constructors. Frame's "no field for which policy" is not this: one completion rule, its N snapshotted. Supersedes "not stored on Sitting" in `showing-limit-not-on-wire` the same day.

### 2026-09-09 — showing-limit-on-sitting: persist N so env change cannot retcon grade — ACCEPTED

**Why:** User spelled the failure: after env changes, grade on an existing sitting would use a new N if it came from compose. Reconstruction from `SittingRepository.get` must carry the opened `showing_limit`. `save` persists the whole aggregate including that field. Same-day confirmation of `showing-limit-on-sitting`.

### 2026-09-09 — session-close: contract-shaping closed — ACCEPTED

**Why:** User closed the session. Status flipped to `closed`. Production signatures plus this pair go in the closing commit.
