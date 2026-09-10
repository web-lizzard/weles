## Current State

**Session closed 2026-09-09.** The shape of change `remember-flow-review-session` (effort `remember-flow`, slice S-01, ACs 01-09) is settled and lives in `frame.md`'s body. Reopen with `/frame remember-flow-review-session` only if a settled decision needs revisiting.

**Genuinely still open, and none of it blocks the next step:**

- **The PRD and stories carry stale wording.** `prd.md` names the default completion as "exhaust what is due"; this session replaced that with a grade-derived rule, so the default pair is now *everything* x *graded `Good` or better, or shown `N` times*. FR-005 and AC-09 are unaffected — they are floors and the stricter rule satisfies them — but the PRD's Non-Goals paragraph describing the default pair is now wrong and someone should correct it.
- **Whether a completed sitting tells the user what is coming back shortly.** Recommended alongside option (d) and never separately confirmed. Presentational, and if taken it must be expressed as interval magnitude over the next-due date, never by reading the scheduler's own state.
- **`intake-overwhelm`, parked.** A due count large enough to discourage the user. Parked rather than rejected: the cheap answer is presentational, a cap on never-reviewed intake stays purely additive later, and there is no backlog in existence yet to observe. Revisit once the surface has been lived with.

**Reversals of duck decisions made here, so a reader of `remember-pillar` is not surprised:** the clock-based reading of option C was replaced by a grade-derived completion rule; the `fuzz-seed` decision to log the randomization draw was found unimplementable and replaced by a seed derived from each event's own facts; and the two policy axes were not built, their justifying variants having become effort-level non-goals. The duck's `session-persistence` decision was upheld, though for the transport reason rather than the one it gave.

## Log

### 2026-09-09 — slice-scope: S-01 is broad and its edges are not yet drawn — OPEN

**Why:** The user opened the session saying the scope for this slice is not crystallized and is open to being arranged jointly. The roadmap fixes the acceptance criteria (AC-01 through AC-09) but not what infrastructure they drag in, and the duck session settled a three-aggregate domain shape whose pieces are not all exercised by those nine criteria.

### 2026-09-09 — same-sitting-return: AC-09 may not fall out of the scheduler for free — OPEN

**Why:** The duck settled option C — the session is only a filter over the frozen set, and learning-phase resurfacing "falls out for free, because the scheduler alone decides when a card comes back" (`context/duck-sessions/remember-pillar/log.md`, `completion-policy` / `session-progress` threads). But `fsrs` 6.3.2 defaults put a `Review`-state card graded `Again` into `Relearning` step 0, due in **10 minutes**, and a `Learning` card graded `Again` back to step 0, due in **1 minute** (`context/efforts/remember-flow/research.md`, "Behaviour that remember must wrap"). A sitting shorter than the relearning step therefore ends with nothing due and the missed card never re-presented — AC-09 unmet, with the session reporting itself complete. "Comes back before the sitting ends" is a promise about the *sitting*; option C delegates it entirely to the *clock*. The two are not the same promise.

### 2026-09-09 — first-session-size: what "due" means for a never-reviewed card, and how big that makes session one — OPEN

**Why:** AC-01 says the session contains every card due at that moment. The duck's lazy wrapping means a card with no `ReviewItem` is "new", and FSRS treats a fresh `Card()` as due immediately (`research.md`, "New Weles card"). The due set is therefore *scheduled-and-overdue* ∪ *never-reviewed*, so the very first session after distill has been running contains every card ever generated. With the PRD's only completion policy being "exhaust everything due" and batch-of-N an explicit effort non-goal (`context/efforts/remember-flow/prd.md`, Non-Goals), AC-01 and AC-02 as written admit no ceiling.

### 2026-09-09 — fuzz-draw-observability: the logged randomization draw may not be obtainable — OPEN

**Why:** The duck kept FSRS fuzz on and preserved the reconstruction invariant by having "the log carry the randomization draw per review entry" (`remember-pillar` log, `fuzz-seed`, ACCEPTED). The library applies fuzz internally inside `review_card` via `random()` and returns only the new `Card` and its own `ReviewLog` of `card_id` / `rating` / `review_datetime` / `review_duration` (`research.md`, "Public surface" and "Behaviour that remember must wrap"). No draw is exposed. Logging the *resulting* interval instead of the draw is possible but changes the log from algorithm-neutral facts into a record of an algorithm's output, which is what the log-as-truth decision existed to avoid. Not yet verified against the library source — the dependency is not installed and `research.md` is the current evidence.

### 2026-09-09 — session-durability: whether S-01 persists a session nothing yet reads back — OPEN

**Why:** The duck settled that `ReviewSession` is persistent and resumable "from the first cut", but the roadmap puts resume in S-02 and expiry in S-02's criteria (AC-10 through AC-13). If S-01 persists sessions, it ships a repository, a frozen membership set, and a lifecycle that no criterion in S-01 exercises — structure without a test. If it does not, AC-01's "opens a session containing every card that is due at that moment" still fixes membership at open, which is most of the aggregate anyway.

### 2026-09-09 — policy-seam: whether the two policy axes are built in S-01 at all — OPEN

**Why:** The duck settled selection and completion as two composing, domain-owned policy axes. The PRD then made **topic- or note-scoped selection** and **batch-of-N / timebox modes** explicit effort-level non-goals, keeping only the default pair (everything × exhaust what is due) (`prd.md`, Non-Goals). No acceptance criterion in the whole effort, AC-01 through AC-22, mentions a topic. A policy abstraction with exactly one implementation per axis and no second one in the effort is the speculative generality the duck itself rejected for options A-D.

### 2026-09-09 — same-sitting-return: not an AC-09 edge case — option C does not terminate a first sitting — OPEN

**Why:** Verified against `fsrs` 6.3.2 source (`fsrs/scheduler.py`, `review_card`), which sharpens the earlier entry of the same day rather than answering it. Defaults are `learning_steps=(1 min, 10 min)`, `relearning_steps=(10 min,)`. In `State.Learning`, `Good` **increments the step and only graduates on the final step** — so a brand-new card graded `Good` at step 0 is due again in **10 minutes**, still in `Learning`, not graduated. `Easy` graduates immediately; `Again` resets to step 0 (1 min). In `State.Review`, `Again` moves the card to `Relearning` step 0, due in 10 minutes.

The consequence is larger than AC-09. Every card in the first sitting is new, so under option C — "the session is finished when nothing in the frozen set is due" — a user grading `Good` finds each card re-entering the due set ten minutes later, and the sitting cannot be completed in fewer than ten minutes nor in fewer than two passes over every card. That is the *main path* of session one, not an edge case. Option C's completion condition and the product's notion of "a sitting" are two different clocks, and option C fused them.

**Consequence:** AC-09 needs a named owner — the session, the scheduler's configuration, or nobody (with FR-005 reworded). This also couples directly to `first-session-size`: an unbounded frozen set multiplied by a two-pass minimum is the first sitting the user actually gets.

### 2026-09-09 — fuzz-draw-observability: confirmed in source — the draw is not obtainable — OPEN

**Why:** `fsrs/scheduler.py` applies fuzz only when `enable_fuzzing and card.state == State.Review`; `_get_fuzzed_interval` computes `(random() * (max_ivl - min_ivl + 1)) + min_ivl` and returns the interval. **The random value itself is not stored or returned anywhere.** The duck's `fuzz-seed` decision — keep fuzz on, and have the log carry the randomization draw per review entry — is therefore not implementable through the library's public interface as written. The disposition is still open: seed the generator per review, log the resulting interval instead of the draw, or disable fuzz.

### 2026-09-09 — sitting-completion: completion derived from grades, not from the clock — OPEN

**Why:** User's proposal, and it is stronger than any option weighed so far. Half of it is already settled ground — the `remember-pillar` duck fixed that the grade scale is product vocabulary owned by the domain. The new move is the second half: **the done-predicate reads the grade already in the log rather than consulting `due_at`.** A card is finished for this sitting once it carries a grade in this session that is not the lowest; the sitting is complete when every card in the frozen set does.

What it fixes, none of which the clock-based option C could:

- **AC-09 becomes a guarantee owned by the session**, not a side effect of the scheduler's minute steps. A lowest-graded card is by construction not done here, so it is re-presented.
- **Completion becomes monotone and terminal.** This closes the hole the duck left explicitly open — "session complete stops being a state and becomes a momentary condition ... which leaves open how a session ever reaches a terminal state so the resumable list does not grow without bound." Under a grade predicate a finished session is finished permanently.
- **The first-sitting two-pass problem disappears.** A new card graded `Good` is done here, regardless of FSRS putting it back in the due set ten minutes later.
- **It costs no new vocabulary.** This is precisely what separates it from the duck's rejected option D, which widened an append-only-forever log with a `graduated-this-sitting` outcome. Reading an existing grade is not widening it.
- **No cursor and no stored order**, so the membership-not-order decision stands and option B stays rejected.
- **The reconstruction invariant is untouched** — the predicate reads `ReviewLog`, which is already the truth.
- **It makes S-02 nearly free**, since done-ness is already scoped by the session id carried as metadata on each review event — a decision the duck had made for other reasons.

The prices, named honestly:

1. The session now owns a notion of "done here" that is **separate from "due"**, which is the second concept option C existed to avoid. The trade is deliberate: option C's single concept could not deliver a bounded sitting or a terminal state.
2. A card graded `Hard` may still be due within minutes by FSRS's reckoning while counting as done for this sitting. The session therefore stops serving everything due inside its own frozen set. That divergence is the honest consequence of (1) and needs stating, not hiding.
3. A card graded lowest repeatedly holds the sitting open with no exit inside this slice — rejection is AC-17, which the roadmap puts in S-04. Bounded only by the user leaving, which is free.

**Open, and the reason this entry is not ACCEPTED:** the predicate needs a ruling on `Hard`. The user named three grades — Again / Good / Easy — and the missing fourth is exactly the one the predicate must decide. In `fsrs` 6.3.2, `Hard` in `State.Learning` **does not advance the step**, so the algorithm treats it as no progress; the product must say whether the sitting does. This also collapses into one question what the PRD had as two: open question 1 (what the four grades are called) and the completion predicate are now the same decision.

### 2026-09-09 — sitting-completion: terminality was oversold — expiry already bounds the list — OPEN

**Why:** Correcting the prior entry of the same day. It claimed the grade predicate "closes the hole the duck left open" about the resumable list growing without bound. The user is right that it does not need to: the duck already settled **lazy expiry from start time** (`session-expiry`, ACCEPTED) with a configured horizon, which bounds that list on its own and costs nothing. So monotone completion buys **no hygiene**. What it still buys is a **product-visible fact** — the slice's own title promises the user can *work through* every due card in one sitting, so "you are finished" has to be something the sitting can say, not merely something that stops being asked. That is a smaller and more honest claim than the one made earlier.

**Consequence:** the argument for the grade predicate rests on AC-09 becoming a guarantee and on the first-sitting two-pass problem dissolving. Both stand. Terminality is a bonus, not a load-bearing reason.

### 2026-09-09 — session-durability: unclosed sessions are harmless, and in S-01 nothing reads them back — OPEN

**Why:** The user's second point collapses into the `session-durability` thread raised at open. Expiry is AC-12, which the roadmap puts in **S-02**, alongside resume. So within S-01 there is no resume and no expiry: an abandoned session is simply never looked at again, and correctness is preserved regardless because `ReviewLog` is the truth and every later session derives its due set from the log — which is also exactly what AC-13 will later guarantee. Unclosed sessions are therefore not a problem this slice has to solve, or can even observe.

What remains genuinely open for S-01 is narrower than the thread first stated: review events carry a `session_id` as metadata (duck, `log-vocabulary`), so a session id must exist and be stable even if nothing ever reads the session row back. Either the session is persisted with its frozen set, or the log carries ids pointing at nothing. The second is not obviously wrong in a slice with no resume, but it is a decision, not a default.

### 2026-09-09 — repeat-counter: a per-card repetition count is derived, not stored, and not algorithm mess — OPEN

**Why:** The user asked whether a per-card repetition counter inside a session is too much mess in the algorithm. It is not mess, and for a reason worth stating: the count is **a query over `ReviewLog`** — review events for this card carrying this session id — so it stores nothing, adds no field, and touches no part of FSRS. It composes with the grade predicate without breaking it: `done = graded above the floor in this session OR seen N times in this session` is still monotone, still derived, still terminal.

The real objection is different: **N is an invented constant**, which is the exact ground on which the duck rejected option A's horizon. That objection is weaker here, because the sitting is now an acknowledged concept with its own rules, so a sitting-scoped constant is in-vocabulary in a way a scheduling horizon was not.

**What makes it more than a stopgap.** It looks like a stand-in for AC-17 rejection arriving in S-04, but it is not only that. Rejection means *this card is bad forever*; a user who simply cannot recall a card today wants *enough of this one for now*, which is the postpone/suspend need the duck named as having **nowhere to live** under the log's scoping rule. A derived repetition count answers that need with no event type and no new vocabulary at all.

**The strongest argument for it comes from the user's own framing of FR-005** — "chodzi raczej o sygnał, że fiszka wróciła", the point is the *signal* that the card came back, not grinding it until it is known. If that is the promise, then N reads not as a safety valve but as **the shape of the promise itself**: a failed card comes back at least once more in this sitting. That is bounded, testable, and matches FR-005 better than an unbounded loop does.

**Still open:** whether S-01 carries N at all, and the `Hard` ruling from the prior turn remains unanswered — a repetition counter does not dissolve it, since `Hard` still decides whether a card returns in the first place.

### 2026-09-09 — repeat-counter: accepted, as the shape of FR-005 and as a configured value — ACCEPTED

**Why:** User accepted the per-card repetition count, and accepted framing it as part of what FR-005 promises rather than as protection against a pathology: a failed card returns in this sitting at least once more. The count stays a query over `ReviewLog` scoped by `session_id`, storing nothing.

`N` is an environment setting for v1, which follows an established precedent rather than adding a mechanism — `backend/src/config/settings.py` already carries `vocabulary_match_threshold`, `card_front_max` and `card_back_max`, and the duck settled the session expiry horizon the same way (`expiry-horizon`, ACCEPTED).

### 2026-09-09 — sitting-completion: the grade-derived predicate stands; only its threshold is open — ACCEPTED

**Why:** Completion of a sitting is derived from the grade recorded in `ReviewLog` for this `session_id`, never from `due_at`. Supersedes the clock-based reading of duck option C for the purposes of this change. The predicate is `done = graded at or above the threshold in this session OR seen N times in this session` — monotone, derived, needing no cursor, no stored order and no new log vocabulary. Where the threshold sits is the one part still open (`hard-ruling`).

### 2026-09-09 — session-durability: S-01 neither resumes nor expires a session — ACCEPTED

**Why:** User accepted that unclosed sessions are not this slice's problem. Resume and expiry are AC-10 through AC-13, which the roadmap assigns to S-02, so within S-01 an abandoned session is never looked at again and correctness holds regardless, `ReviewLog` being the truth. **Consequence:** the frame body records that no session lifecycle beyond opening exists in this change. The `session_id` residue stays open — review events carry one, so an id must be stable even where no session row is read back.

### 2026-09-09 — hard-ruling: the cross-session half is already answered by the algorithm — OPEN

**Why:** The user asked whether `Hard` should return, reasoning that it also signals something not yet known, and asked separately whether it returns in the **next** session. Those are two clocks and only one of them is a product decision:

- **Across sessions: already answered, and not ours to decide.** `Hard` yields a shorter next interval than `Good` — that is what the rating means in FSRS — so the card returns sooner in a later session automatically. In `State.Learning` it is stronger still: source read of `fsrs/scheduler.py` v6.3.2 confirms `Hard` **leaves `card.step` unchanged**, so a new card graded `Hard` makes no progress toward graduating and must be met again. The "still needs work" signal is therefore delivered across sessions with nothing added.
- **Within the sitting: the only open question**, and much smaller than it looked — whether the sitting *also* delivers that signal immediately.

**Correction to an earlier turn.** It was stated that a threshold stricter than "lowest" would force a retouch of FR-005 and AC-09. That is wrong and it changes the decision: both are phrased as a **floor** — "a card graded lowest comes back within the same sitting" — so a rule that also returns `Hard` cards satisfies them rather than contradicting them. The stricter threshold is additive, and costs no PRD or stories revision.

With that cost removed, the argument favours **threshold at `Good` or better**: it mirrors what the algorithm already does in `Learning` (no step advance on `Hard`) rather than inventing a product rule, it matches the user's stated intent, and `N` bounds the cost at one extra showing. Not settled — the user's sentence was ambiguous and the ruling is theirs.

### 2026-09-09 — hard-ruling: the sitting's threshold is `Good` or better — ACCEPTED

**Why:** Confirmed by the user. A card leaves the sitting on `Good` or `Easy`, or on exhausting its showings. `Hard` does not finish a card within the sitting, mirroring `fsrs` 6.3.2's own treatment in `State.Learning`, where `Hard` leaves `card.step` unchanged. Additive to FR-005 and AC-09, which are floors, so no PRD or stories revision is owed. Two consequences fall out rather than being chosen: "best grade" and "last grade" coincide, because a card stops being served the moment it is done; and one `N` covers both `Again` and `Hard`, so the sitting has a single knob.

### 2026-09-09 — sitting-order: random within a round, drawn from the least-seen cards — ACCEPTED

**Why:** User's proposal, and it is the right one. The next card is drawn uniformly at random from the undone cards with the **fewest showings in this session**; a card that has just been shown leaves that pool until the rest of the round catches up. Stated as the invariant the user asked for: *no card is presented while another undone card in the frozen set has a strictly lower showing count.*

What it buys:

- **It is derived, like everything else.** The showing count is the same `ReviewLog` query already established for the repetition counter — no cursor, no stored order, nothing added to the model.
- **It solves the immediate-repeat problem without a rule.** A card just graded `Again` now sits above the round minimum and cannot be drawn again until the round completes, so the user never sees an answer followed straight away by the same question. Spacing falls out of the invariant.
- **It makes `N` do double duty.** Round *k* is the *k*-th pass over what is still undone, and a card is finished by count at `N`, so the sitting is **at most `N` rounds**. One configured number now explains the whole shape of a sitting.
- **Random beats the alternatives on merit, not by default.** Due-order no longer means anything inside a sitting once completion left the clock, and insertion order tracks generation order, which clusters cards drawn from the same note and cues the user. A random draw breaks that clustering.

**Consequence — a second source of randomness, and it is the harmless one.** Remember now has two: FSRS's interval fuzz, and this ordering draw. They differ in exactly the way that matters to `fuzz-draw-observability`: the ordering draw **affects no card's schedule**, so the duck's log scoping rule ("the log accepts exactly those events that change the derived schedule") keeps it out of `ReviewLog` by construction, and the reconstruction invariant never sees it. It needs an injectable source for deterministic tests, and nothing more. Fuzz is a problem precisely because it is the other kind.

### 2026-09-09 — fuzz-draw-observability: three responses weighed, seed-from-the-log recommended — OPEN

**Why:** Source read of `fsrs/scheduler.py` v6.3.2 confirms the mechanism precisely: the module does `from random import random`, so the draw comes from the **process-global** `random.Random` instance, and `Scheduler` exposes **no seed or RNG injection point** at all. Three responses are available.

**A — seed the global generator per review, from data already in the log.** Seed immediately before `review_card` with a value derived from the review event itself (`card_id`, `reviewed_at`, grade). The draw becomes a pure function of facts the log already holds, so replay reproduces it exactly and **nothing extra is logged** — zero bytes added to `ReviewLog`.

This fulfils the duck's `fuzz-seed` intent better than the duck's own mechanism. That decision wanted the log to carry the draw so replay stays faithful; it assumed the library exposed the draw, which it does not. Deriving the seed from the log entry carries the draw *implicitly* and perfectly. It also loses nothing fuzz is for: interval fuzz exists to stop cards reviewed together from clumping onto the same day forever, which is decorrelation **across cards**, not irreproducibility **across replays**. Different `card_id` and `reviewed_at` still give different draws.

**B — log the resulting interval instead of the draw.** Rejected on principle. The duck fixed the log as `card_id`, `reviewed_at`, `grade` — "what stays true across any algorithm". An interval is an algorithm's *output*, so B turns the log from algorithm-neutral truth into a cache of FSRS's decisions, and makes the reconstruction invariant vacuous: rebuilding would read the answer back rather than recompute it. That guts the test the entire design rests on.

**C — disable fuzz.** Reverses the duck's `fuzz-seed` decision, and costs more here than elsewhere because of `first-session-size`: the first sitting's due set is every card distill ever generated, so without fuzz that entire cohort graduates together and returns on the same day, permanently. Clumping is exactly what fuzz prevents, and this slice produces the largest clump the system will ever see. The two threads interact, and they argue against C.

**The honest cost of A, and why it is acceptable.** Seeding works only because the library draws from the global `random` module once per fuzzed review — an implementation detail, not a public API guarantee, so a library upgrade could silently invalidate it. It is not silent, though: the reconstruction invariant's own test catches it. If a future version drew from its own `Random()` instance or from `secrets`, seeding would stop determining the draw, the forward pass and the rebuild would diverge, and the test would fail loudly. A version bump also already invalidates memoized state through the parameter stamp, so the two mechanisms compose.

**One interaction to respect.** Seeding the global generator perturbs every other consumer of `random` in the process, including the `sitting-order` draw settled this session. That draw must therefore use its own `random.Random` instance — which it wants anyway for injectable, deterministic tests.

### 2026-09-09 — fuzz-draw-observability: option A accepted — nothing is stored, and it is the schedule that rebuilds — ACCEPTED

**Why:** User accepted A, restating it as "we store the seed in the session". Two corrections, and both matter.

**No seed is stored anywhere, and a session-level one would break the invariant it is meant to protect.** Under A the seed is *derived* per review event from `card_id`, `reviewed_at` and grade — facts already in `ReviewLog` — so there is nothing to persist and nothing that can drift. A seed stored once per session would be the wrong granularity, not merely a redundant one: fuzz is drawn per review, so a single session seed makes each draw depend on the **order and count** of `review_card` calls in that sitting. This session settled that ordering is random and deliberately absent from `ReviewLog` (`sitting-order`), so replay could not reproduce that sequence — the schedule would become dependent on an unlogged fact, which is exactly the failure the reconstruction invariant exists to catch. Per-review derivation makes each draw independent of the sitting entirely.

**What is guaranteed is reconstruction of the *schedule*, not of the *session*.** The invariant is the duck's: a `ReviewItem` — `due_at` plus `scheduler_state` — must be deletable and fully rebuildable from `ReviewLog` without changing the schedule. Replaying a card's review events in `reviewed_at` order, seeding each from its own fields, reproduces the same due date including fuzz. The sitting itself — which card appeared when, how many rounds it ran — is **not** reconstructible and does not need to be, for the same reason the ordering draw was free: it changes no card's schedule. `session_id` appears in the log only as metadata scoping the sitting's own queries, never as an input to replay.

### 2026-09-09 — reviewed-at-authority: the logged timestamp must be the one handed to the scheduler — ACCEPTED

**Why:** Fell out of walking the seed through algorithmically. Replay reproduces a schedule only if every input is identical, and `review_datetime` is an input to FSRS's interval arithmetic quite apart from the seed. If the log stored a rounded or re-derived timestamp while the adapter passed a full-precision one, replay would diverge for reasons having nothing to do with fuzz. So `reviewed_at` is captured once, written to `ReviewLog`, and handed to the scheduler — one value from one source, timezone-aware UTC, which the library requires on pain of `ValueError`. This is the concrete form of a risk the duck named in the abstract: "a bad `reviewed_at` corrupting everything downstream of it."

Also settled by the same walk: the adapter seeds **unconditionally**, before every `review_card` call, rather than only when it expects fuzz to fire. Fuzz applies only in `State.Review` at intervals of 2.5 days or more, but making the adapter reason about when the library draws would couple it to a second implementation detail. Seeding always costs nothing and removes that reasoning.

### 2026-09-09 — sitting-vs-due: finishing a sitting does not mean nothing is due — OPEN

**Why:** Exposed by walking the user scenarios. A sitting ends when every card is graded `Good` or better, or has exhausted its showings. But FSRS's learning steps mean a card graded `Good` at step 0 is due again in **ten minutes**, still in `Learning` and not graduated (source-verified earlier this session). So a user who completes a sitting and immediately reruns the command gets a **new session containing the cards they just finished**.

This is not a defect — it is correct spaced repetition, and it is how established tools behave. But it means **"you are finished" and "nothing is due" are two different statements**, and AC-02 is written about the second one: "starting a review when nothing is due tells the user so and creates no session." Immediately after a completed sitting, cards *are* due, so AC-02's branch does not fire and a full session opens instead. To the user that can read as the app not having registered the work they just did.

Worth seeing plainly: the clock problem that drove this whole session was not eliminated by the grade predicate, it was **moved across the session boundary**. Inside a sitting it is solved; between two sittings minutes apart it reappears in a milder, product-visible form.

Responses, none argued yet: accept it as correct behaviour and say nothing; have the opening of a session distinguish cards in learning from cards genuinely due again, which is presentation rather than domain; or exclude recently-graduated cards from a new frozen set, which reintroduces the horizon constant the duck rejected in option A and should probably lose on those grounds.

**This also sharpens `first-session-size`.** The two threads share a shape: what AC-01's "every card that is due at that moment" means is doing more work than its wording admits, both at the top end (the whole backlog) and immediately after a sitting (everything still in learning).

### 2026-09-09 — sitting-vs-due: the "distinguish learning cards" response must not read FSRS state — OPEN

**Why:** Raised while answering the user's question about what `State.Review` is. One of the three responses sketched for `sitting-vs-due` was to distinguish, when a session opens, cards still in learning from cards genuinely due again. Taken literally that means reading FSRS's `State`, which is **the algorithm's state model** — exactly what `distill-domain-shape` forbids from leaking upward and what the duck's opaque `scheduler_state` blob exists to contain. The domain would learn a word it must not know.

There is an algorithm-neutral form of the same distinction, and it survives: **the magnitude of the interval**. "Due again within the hour" versus "due today" is a fact about `due_at`, which is already a real domain field kept deliberately outside the blob. Every scheduler produces it, no state vocabulary is imported, and the same decision that made the completion predicate a pure function pays off a third time.

So the response stays available, but only in its neutral form. The state-reading form should be rejected outright if it comes up during planning.

### 2026-09-09 — state-home: the blob is where the memory model is cached, not where it lives — ACCEPTED

**Why:** The user asked whether FSRS's memory model will live in a per-card database field. Materially yes — a per-card record holds `due_at` as a real indexed domain field, an opaque `scheduler_state` (the adapter's `Card.to_dict()`) the domain never looks inside, and a stamp naming the algorithm and its parameter version, created lazily on first review so absence still means "never reviewed".

But the phrasing needs correcting, because it is the exact mental model the duck built the design to prevent. **The memory model lives in `ReviewLog`; the field is a memoization of it.** The duck's invariant is that a `ReviewItem` must be deletable and fully reconstructible from the log without changing the schedule, and the reason given was that an adapter owning its own persisted state "lies about being replaceable" — the port looks swappable while the state pins the algorithm in place. Reading the blob as the home of the model rather than as a cache of it is how that guarantee quietly dies, one convenience at a time.

Three consequences that only make sense under the cache reading, and are worth stating because they are what the reading buys: the blob is **discardable at any moment**, which is what makes the lazy stamp check on the read path work with no worker; `due_at` is duplicated inside `Card.to_dict()` and that copy is **never read**, the domain using only its own field; and the domain **never imports `fsrs`** at all, the blob being opaque data to it and serialization living entirely in the adapter.

Not new ground — this is the duck's `scheduler-state-home` decision restated. Recorded here because the frame body is what `/plan` and `/discover-contracts` read cold, and the distinction has to survive into them.

### 2026-09-09 — seed-scope: the seed has no part in composing a session — ACCEPTED

**Why:** The user twice credited the per-review seed with something it does not do, this time with making session composition work out. It contributes nothing there. Delete the seeding entirely and the frozen set of every session is byte-identical. The seed buys exactly one property: a rebuild from `ReviewLog` reproduces the same numbers as the original forward pass. That is a property of **replay**, not of **selection**.

What actually composes a session is one query: a card is in the frozen set when it has no scheduling record at all, or its `due_at` is at or before now. That query runs the same with fuzz off, with no seed, or behind a different scheduler entirely — which is the point, since `due_at` was deliberately kept outside the opaque blob so it could be queried algorithm-neutrally.

The division worth carrying into planning: **the scheduler decides *when* a card is next due; the session query decides *what is in the sitting*; neither knows the other's vocabulary.** Cards in `Learning` appear a few minutes after being graded and cards in `Review` after days, but the query never learns those words — it only compares dates.

### 2026-09-09 — composition-on-the-clock: the reframe both remaining threads share — OPEN

**Why:** `first-session-size` and `sitting-vs-due` are one problem seen from two ends, and the user's assumption that it is already handled is what exposed the shape.

AC-01 reads "a session containing every card that is due at that moment". Two situations make that wording carry more than it admits. At the top end, the very first run: no card has a scheduling record, so every card distill has ever produced is due, and the sitting is that entire backlog multiplied by up to `N` rounds. Immediately after a completed sitting: every card graded `Good` at learning step 0 sits at step 1, due in ten minutes, so rerunning the command reopens over the cards just finished.

**The common root, and it is a reframe this session has already performed once.** "Due", as the scheduler computes it, is a **scheduling** concept, and AC-01 borrowed it as a **sitting-composition** concept. Those are not the same thing — which is exactly the separation made earlier for completion, when the done-predicate was lifted off `due_at` and put onto grades. Completion was taken off the clock; **composition was not.** Both symptoms are that one omission.

Options for what bounds the frozen set at open:

- **(a) Nothing — AC-01 read literally.** The sitting may be the whole backlog.
- **(b) A cap on cards in the sitting.** This is batch-of-N, an explicit effort non-goal in `prd.md`. Blocked without reopening the PRD.
- **(c) A cap on how many never-reviewed cards enter one sitting** — the "new cards per day" knob familiar from existing tools. Genuinely distinct from (b): it bounds intake, not the sitting, so it is not literally the non-goal. But it is a knob nobody asked for in this slice.
- **(d) Nothing, on the grounds that it does no harm.** Everything settled this session supports it: walking away is free, every grade given is permanent and has already moved its card, and the remainder is still due next time. A large frozen set is then just a number the user never has to exhaust.

**Recommendation, not yet put to the user in argument:** (d) for `first-session-size`, with the boundary stated explicitly in the body so planning does not invent a cap; and for `sitting-vs-due`, accept the behaviour but let a completed sitting say what is coming back shortly, expressed as interval magnitude over `due_at` and never as FSRS state. The one honest cost of (d) is that the slice's own title promises the user can work through every due card in one sitting, and with a large enough backlog that is unkeepable — though arguably by arithmetic rather than by design.

### 2026-09-09 — composition-on-the-clock: option (d) accepted — nothing bounds the frozen set — ACCEPTED

**Why:** User took (d). No ceiling is placed on the frozen set: a sitting may contain the entire backlog, and a card is in it when it has no scheduling record or its `due_at` has passed. The supporting argument is everything this session already settled — leaving is free, every grade given is permanent and has already moved its card, and the remainder is still due next time — so a large set is a number the user need never exhaust rather than an obligation. Recorded as an explicit boundary so planning invents no cap of its own.

**Consequence worth carrying downstream:** with a large first due set the sitting will not reach completion on the first run, so the completion machinery designed at length this session is **not exercised by the natural first-run path**. Acceptance scenarios must construct a small due set deliberately rather than rely on a fresh system's own state.

### 2026-09-09 — intake-overwhelm: a due count large enough to discourage the user — PARKED

**Why:** The user raised it while accepting (d), and flagged it as a hypothesis they could not support. It is better supported than they credited: established spaced-repetition tools carry a "new cards per day" limit for exactly this reason, which is strong prior art. Prior art is not evidence about *this* product, though, and there is no backlog in existence yet to observe.

Parked rather than rejected, on three grounds:

1. **The concern is about presentation, not composition.** If the discouragement comes from being shown "412 due", the cheap answer is to stop leading with the number, or to frame it as an offer rather than a debt — surface work that changes no domain decision and reopens no PRD non-goal.
2. **(d) is reversible and (c) is not cheaply.** Adding a cap on never-reviewed intake later only narrows an existing query; nothing built under (d) would have to be undone. Building it now means inventing a default with no data to set it from.
3. **It is the same call the duck already made about parameter optimization** — parked not on cost but because there is no history to fit against until the pillar has been used.

Revisit once a real backlog exists and the surface has been lived with.

### 2026-09-09 — session-durability: the question was never durability — a sitting spans requests — ACCEPTED

**Why:** Grounded rather than argued to a preference, and it reverses the framing this thread carried since it was opened.

Two facts from the repository settle it. First, `backend/src/adapters/db/` holds nothing but `__init__.py`, and every repository lives under `backend/src/adapters/out/in_memory/` — so "persisting" anything in this prototype means an in-memory repository that dies with the process. Durability across restarts is therefore not on offer for any aggregate, and asking whether S-01 should have it was the wrong question.

Second, and decisively: `backend/src/adapters/http/` exposes per-feature routers and the TUI is a separate Ink process (duck, `tui-stack`), so **each user action in a sitting is its own request**. Revealing a back, grading a card and asking for the next one cannot share process memory. The session must therefore be retrievable by its identity between requests, or the sitting cannot exist at all.

So `ReviewSession` is a repository-backed aggregate in S-01 — one port with `save` and a `get`, plus an in-memory adapter, matching `NoteRepository` and `CardRepository` in `backend/src/domain/distill/ports.py`. It is not written-and-never-read: every one of AC-03 through AC-09 reads it back.

**This corrects two earlier readings.** The objection raised when this thread was opened — that S-01 would ship a repository no criterion exercises — is wrong; the criteria exercise it on every card. And the concern that persistence would leak S-02's work backwards is also wrong: persistence was never S-02's to own. S-02 adds **expiry and offering a session for resumption**, which are genuinely absent here. The duck's "persistent and resumable from the first cut" was right, though it gave the TUI-gesture reason rather than this one.

The `session_id` on review events stands, and now points at something real. It is what scopes showing counts and the completion predicate, and keeping the sitting's state as log queries rather than process memory is what makes S-02 additive instead of a rewrite of the predicate.

### 2026-09-09 — session-contents: the session holds intent; the log holds what happened — ACCEPTED

**Why:** The user spotted the tension directly — if everything is derived from `ReviewLog`, what is left in `ReviewSession`? Working it through gives a sharp division and a very small aggregate.

**What it must hold, because the log cannot say it:**

- **Its identity**, which is what every review event carries and what scopes the sitting's queries.
- **Frozen membership** — the set of card ids chosen when the sitting opened. This is the irreducible part and the reason the aggregate exists at all: a card that was in the set but never reached has **no log entries whatsoever**, so no query over the log can discover that it belonged. Membership is precisely the fact the log cannot reconstruct.
- **Its start time**, following the `created_at` convention already on distill's `Card`. Named honestly: nothing in S-01 reads it, and S-02's expiry derives from it. It is a fact about the entity rather than structure built ahead of a need.

**What it must not hold, all of it derived from the log scoped by the session id:** how many times each card has been shown, which cards are done, how far along the sitting is, what the next card is, any cursor or stored ordering.

**The division in one line: the session records what you set out to work through; the log records what you actually did.** That is why both exist, and why neither duplicates the other.

**Two consequences worth carrying forward.** The aggregate is **write-once** — saved when the sitting opens and never mutated, since expiry too is derived from the start time — so the repository is effectively a lookup of the sitting's intent, which is exactly what duck option C meant by "the session is a filter". And a card discarded in distill mid-sitting is **filtered out on read** rather than removed from the stored set, keeping membership immutable and matching the duck's rule that candidates come from the port so a vanished card simply stops being selected.

The only remaining candidate for a fourth field is the completion policy the duck wanted persisted and frozen at start, which is the open `policy-seam` thread and nothing else.

### 2026-09-09 — session-contents: membership is derivable after all — the earlier "irreducible" claim was wrong — OPEN

**Why:** Correcting the previous entry of the same day, which asserted that frozen membership is the irreducible fact justifying the aggregate because a card never reached leaves no log entry. That reasoning has a hole. Membership **is** derivable from a start time plus state already held:

> a card is in the sitting when its next-due date is at or before the sitting's start time, **or** it has a review event carrying this session id.

The second clause recovers exactly the cards the first loses. A card graded during the sitting has a due date pushed past the start time and would drop out of the first clause, but its own log entries put it back. A card never reached still satisfies the first clause. A card that became due *after* the sitting opened is correctly excluded. So the aggregate could hold nothing but an identity and a start time.

**Recommendation is still to store the set**, on a stated ground rather than the false one: the derivation is only correct while **nothing but this sitting moves a card's schedule**. That holds today — one user, no worker, one sitting at a time — and it is exactly the sort of assumption that rots silently. A postpone or suspend capability, which the duck already named as having nowhere to live, would retroactively corrupt the membership of every past sitting. One stored field is immune and cheap.

### 2026-09-09 — session-as-events: session lifecycle stays out of `ReviewLog` — ACCEPTED

**Why:** The user asked whether `ReviewSession` is needed at all, or whether separate events on the log would do. The duck ruled on this by name and the ruling holds, with one new reason it did not have.

The duck's `log-vocabulary` decision set the scoping rule — "the log accepts exactly those events that change the derived schedule, and nothing else" — and drew this exact conclusion immediately: session lifecycle does not belong in `ReviewLog`, because "opened" and "expired" change no card's schedule; a session id stays as metadata on a review event, never as an event of its own. The justification was that only schedule-affecting events are held in shape by the reconstruction invariant, so anything else enters untested and remains as dead weight in replay. A `session_opened` event carrying several hundred card ids would be walked by every replay forever while being incapable of affecting the result, and replay would need type dispatch for a branch that can never matter.

**The new reason, which this session produced:** the sitting was settled last turn as **write-once and never mutated**. An event stream's entire advantage is recording change over time. For an entity that never changes, a stream is a row with extra steps. The user's instinct — everything should be the log — is right as a principle, and the sitting is the one thing that is neither derived from the log nor ever changed, which is precisely why it is the exception.

A separate second event stream for sessions was also considered and rejected on the same grounds: more machinery for a fact that never moves, and no resume in this slice to justify it.

### 2026-09-09 — session-contents: the set is stored — deriving it would save a column, not a table — ACCEPTED

**Why:** The user asked whether a session repository is needed at all, or a port and adapter onto the log with the aggregate rebuilt from it. That question settles the membership question left open in the previous entry, by removing the only thing that made deriving attractive.

**A session row is unavoidable, for a reason independent of membership.** The sitting exists as a server-side fact from the moment it opens, before any grade is given: AC-01 opens a session, AC-03 reveals a back, AC-05 grades — each is its own HTTP request against a separate Ink process. Between opening and the first grade the sitting has **no review events at all**, so nothing in the log identifies it, and the identity and start time must already be somewhere server-side or the second request cannot find the sitting. The alternatives both fail: writing a synthetic opening event puts session lifecycle back into `ReviewLog`, which was rejected; letting the client hold the identity and the frozen set moves domain state into the frontend and leaves the server unable to validate it.

**So the row exists regardless, and deriving membership would save a column rather than a table.** That inverts the earlier trade: the derivation's cost is unchanged — it holds only while nothing but the sitting moves a schedule — while its benefit shrinks to one field. Frozen membership is stored.

### 2026-09-09 — slice-scope: the slice's seams, counted — ACCEPTED

**Why:** Answers the question the user opened this session with: the scope is broad and assumed to include a port and adapter for spaced repetition. It includes **five** seams, and naming them is the honest measure of the slice.

1. **Scheduling** — remember's own port, with the `fsrs` 6.3.2 adapter behind it. The port hides the algorithm's state model; the adapter owns the seeding, the grade-to-rating mapping and all serialization.
2. **Card candidates and content** — remember's port onto distill, resolving a scope to candidate card ids plus the front and back a review renders. Duck settled that this read exists the moment anything appears on screen, independently of topic selection.
3. **The sitting** — a repository for a write-once aggregate, saved at open and read on every subsequent request.
4. **Review events** — append and query. Note its shape: nothing ever loads "the log" as a whole, so the port saves one event and answers queries by card and by sitting. `ReviewLog` as an aggregate is a modelling convenience; what is persisted is individual events, which also keeps the repository to a single `save`.
5. **Per-card scheduling state** — a repository for the memoized record, whose contents are a cache of the log and discardable at any time.

All five sit behind in-memory adapters, since `backend/src/adapters/db/` is empty and every existing repository lives under `backend/src/adapters/out/in_memory/`.

**On rebuilding the aggregate from the log:** what the application works with during a sitting is the stored row **plus** facts derived from the log at that moment — showing counts, which cards are finished, which card comes next. The stored part is what the sitting intended; the derived part is what has happened since. Neither is complete alone, and that division is what keeps the session small.

### 2026-09-09 — log-session-relation: one field, one direction, invisible to replay — ACCEPTED

**Why:** The user asked for the relationship to be made explicit. It is deliberately thin, and its thinness is what lets both designs hold at once.

**Direction.** A review event carries the sitting's identity; the sitting holds no reference to its events. The direction is forced by the sitting being **write-once**: were it to track its events, it would be mutated on every grade. Events are the growing thing, the sitting is fixed.

**The property that matters — the identity is invisible to replay.** Reconstruction of a card's schedule reads `card_id`, `reviewed_at` and grade, groups by card, and **never reads the session id at all**. The sitting's own queries read `card_id` and the session id, group by sitting, and never touch the schedule. One event stream, two orthogonal readers, disjoint field usage.

This is exactly why the session id is admissible on the event while a `session_opened` **event** was not, and the distinction is sharper than the duck's scoping rule alone conveyed. A session lifecycle event would be *visible* to replay as a record it must recognise and skip. A session id is a field replay simply does not read — inert to the reconstruction invariant rather than exempted from it.

**No domain-level dependency in either direction.** The log knows nothing of `ReviewSession`, carrying only an opaque identifier; the sitting knows nothing of events. Neither type references the other, and the join lives in the application layer, consistent with the duck's hexagonal, CQRS-lite, application-owned `UnitOfWork` ground.

**Lifetimes differ, deliberately.** Events are permanent; a sitting is not — with in-memory repositories it dies with the process. So an event may carry the identity of a sitting that no longer exists, which is ordinary history rather than breakage, and is what AC-13 will later formalise as grades from an expired session still counting.

**One asymmetry worth carrying into planning.** Grading writes two things: the event and the updated per-card scheduling record. They belong in one unit of work, but the failure modes are not symmetric, and the reconstruction invariant says which way to fall. Losing the memoized record is recoverable — it rebuilds from the log by definition. Losing the event is not: the schedule would have moved with nothing recording why, and reconstruction would produce a different answer than the stored state. **The event is the write that must not be lost.**

### 2026-09-09 — mental-model: what survives deletion is the clearest statement of the design — ACCEPTED

**Why:** The user offered a mental model — the log lives permanently and tracks a card's life, the sitting is a moment in time in which the user performs reviews. Substantially right, with two refinements and a missing third element.

**The log tracks *recall history*, not the card's lifecycle.** A card's life — born, worded, discarded — belongs entirely to distill. Remember's log records exactly one kind of fact: at this moment, this card was recalled at this grade. Keeping that distinction is what keeps the pillar boundary intact, and it is why the one write remember makes back into distill is a rejection command rather than anything about a card's content.

**The sitting does not perform reviews; it frames them.** The user performs the reviews and each is an event. The sitting only says *these cards, from this moment*. Duck option C's word for it was a filter, and nothing since has made it more than that.

**The third element the model was missing** is the per-card memoized record, which sits between the two: permanent-looking, but derived.

**The sharpest form of the whole model is what survives deletion:**

- Delete `ReviewLog` and everything is gone. It is the only irreplaceable thing in remember.
- Delete a card's memoized scheduling state and nothing is lost — it rebuilds from the log, which is the invariant the design is built on.
- Delete every sitting and no schedule changes at all. Only convenience is lost. The duck's phrase was that sessions are "disposable by construction rather than by decision".

### 2026-09-09 — policy-seam: build the behaviour, not the seam — OPEN

**Why:** Opening the last thread with the argument rather than deferring it again.

**The two positions.** The duck settled selection and completion as two composing, domain-owned policy value objects, and defended that against its own charge of speculative generality on one ground: as an abstraction over technical options A-D it would be speculative, since those would never coexist, but as **session mode** the variants are real, product-visible, chosen per session and named in review vocabulary — exhaust everything due, a fixed batch of N, a timebox. The PRD then made **topic- or note-scoped selection** and **batch-of-N and timebox modes** explicit effort-level non-goals, deferring precisely the variants that justified the abstraction.

**So the duck's own test now fails.** With one selection and one completion rule in existence, and the second of each ruled out for the whole effort, nothing would ever be swapped. A policy value object with exactly one implementation is an interface with one implementer — the same dead branch `distill-domain-shape` cut when it removed the `rejected` status for adding a branch that could not be exercised.

**Recommendation: build the behaviour, and name it well.** The completion rule is an explicit, named domain concept — not a strategy interface, not a registry, not a parameter chosen per sitting. When a second rule is genuinely wanted, introducing the seam is a refactor of one call site, which is cheap precisely because the rule is already named and in one place.

**Which also settles the fourth field.** The duck wanted the completion policy persisted and frozen onto the sitting so a resumed session keeps the rules it began under. With exactly one rule, that field stores a constant and is not earned. The live residue is subtler and worth stating: the rule has a **parameter**, the configured showing count, and freezing *that* would be the honest form of the duck's decision. In v1 it is moot — the count is an environment setting and sittings live in memory, so a sitting cannot outlive a change to it, and the asymmetry the duck worried about cannot be observed. The field is earned when a sitting can survive a configuration change, which is not this slice.

**Note for the PRD's own wording**, which has gone stale: it names the default completion as "exhaust what is due", and this session replaced that with a grade-derived rule. The default pair is now *everything* × *graded `Good` or better, or shown `N` times*.

### 2026-09-09 — policy-seam: the sitting stores the result of selection, which is what makes filters extensible — OPEN

**Why:** The user asked whether building `ReviewSession` is what lets more sophisticated filters — a sitting scoped to a topic, or several — be added later. It is, and the reason strengthens the case for skipping the policy seam rather than weakening it.

**The extension point already exists, because the sitting stores the *result* of selection and not the *rule*.** Its frozen set is a set of card ids; how they were chosen is recorded nowhere and needs to be. Everything downstream — the completion rule, the round ordering, the log, replay — operates on "the frozen set" and cannot tell where it came from. A selection policy value object would represent the rule; storing the resolved set decouples everything without representing anything.

What a topic-scoped sitting would actually touch, later: the command gains topic ids, already resolved by capture, since the duck settled that fuzzy recognition happens there and the port selects by exact id; the port resolves `topic_id → note_ids → card_ids` inside distill as a two-hop join; the frozen set is filled from that rather than from everything; and an empty resolution refuses the session. Nothing else moves.

**For the same reason the port should not take a scope argument in this slice.** One parameter with one possible value, "everything", is a branch that cannot be exercised — the same objection as the policy value object, at smaller scale. Widening the signature later touches one port, one adapter and one caller.

**And this session removed an obstacle the duck had flagged for exactly this future.** The duck observed that not every pair composes: a selection ignoring due-ness — cramming a topic before an exam — would leave the default completion policy finishing instantly, because nothing in the set is due, so "a selection axis that can ignore due-ness therefore forces at least one completion policy that is not due-based". The completion rule settled here **is not due-based**: a card is finished when graded `Good` or better, or shown `N` times, and due-ness plays no part. The second completion policy the duck thought a topic selection would force is therefore no longer forced. Topic-scoped sittings compose with the default rule as it now stands, which is a coupling this session dissolved as a side effect.

### 2026-09-09 — policy-seam: what "behaviour, not seam" means concretely — OPEN

**Why:** The user asked for the distinction spelled out. In one line: **a seam is a place where a decision can be substituted; the behaviour is the decision itself.**

**The seam version** is a protocol for the completion rule, at least one implementation of it, a discriminator field persisted on the sitting saying which rule it began under, and something that resolves that stored value back to an implementation. Then the same again for selection. The tests that come with it assert the protocol boundary and the resolution step in addition to the rule.

**The behaviour version** is one named domain concept that takes the frozen set and the sitting's review events and answers both questions — is this card finished here, is this sitting finished — called directly by the one application service that needs it. No protocol, no discriminator, no resolution.

**"Name it well" is the part that carries the weight, and it is not decoration.** The rule must not be scattered as an inline condition inside a request handler; it is one concept, in one place, named in review vocabulary rather than algorithm vocabulary — the same test the duck applied to the grade scale. That is precisely what makes the later refactor cheap: extracting a named concept in one place into a protocol and adding a second implementation is mechanical, whereas extracting a condition inlined across three handlers is not. The seam is deferred, not made expensive.

**What the seam would cost now:** a discriminator persisted on a sitting that this session established as write-once and whose extra field is unearned; a branch that cannot be exercised, which is exactly what `distill-domain-shape` removed the `rejected` status for; and tests asserting polymorphism nobody uses.

**One distinction worth guarding, because it is easy to conflate.** The round ordering needs an injectable random source so tests are deterministic. That is a seam for controlling a non-deterministic dependency, not for substituting a business rule. Injecting the generator is right; making the ordering a substitutable strategy is the same unearned abstraction as the policy object, and the two must not be confused during contract shaping.

### 2026-09-09 — policy-seam: behaviour, not seam — ACCEPTED

**Why:** User accepted. No policy protocol for selection or completion, no implementation registry, and no discriminator field on the sitting. The completion rule and the ordering rule each exist once as a named domain concept, called directly by the one application service that needs them. The distill port takes no scope argument while "everything" is its only possible value.

The grounds, argued across the preceding entries: the duck's defence of the two policy axes rested on session *modes* being real, product-visible and chosen per sitting, and the PRD then made every one of those modes an effort-level non-goal, so the duck's own test — would anything ever be swapped — now fails. The sitting's frozen set already stores the **result** of selection rather than the rule, which is what makes topic-scoped sittings a later change to one query rather than a new abstraction. And naming the rule in one place is what keeps the deferred seam cheap to introduce.
