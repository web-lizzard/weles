## Current State

Session closed. Everything that shapes behaviour is in `frame.md`'s body. One thread is
genuinely still open and travels forward unresolved:

**Naming the fifth outcome.** The user said "discarded". That is `distill`'s word for the
whole removal mechanism, machine-made ones included; `user_audit` is the reason code that
isolates the user's judgement. Whether `remember`'s outcome should borrow `distill`'s noun —
and thereby name across the boundary it is deliberately not writing across — is a naming
question, not a behaviour one. `/discover-contracts` decides it.

Three scope facts the next step inherits, established here but not boundaries:

- `remember`'s `UnitOfWork` carries no outbox appender; capture's and distill's do. Writing
  the rejection and its envelope atomically needs one.
- `distill` has no manual-discard command. The audit surface
  `context/adrs/distill-domain-shape/decision.md:112` refers to does not exist yet, so this
  change builds the first one.
- The post-reveal gate has no backend enforcement and needs none — it is inherited from
  AC-05's existing TUI-level convention. `/plan` should not invent a guard for it.

## Log

### 2026-09-11 — port-into-distill: rejection needs a write path into distill — OPEN

The user opens the session naming a boundary-crossing write port as the change's main risk,
and floats outbox-plus-local-cleanup as a way to avoid it.

**Why:** Raised, not yet resolved — the framing has not been separated from its proposed
solution, and the observation ("rejection must reach distill") has not been distinguished
from the acceptance criterion actually on the slice (AC-17 speaks only about offering).

### 2026-09-11 — sitting-pin: a sitting pins its card set, but only as a ceiling — ACCEPTED

`Sitting.card_ids` is frozen at open and `uow.sittings.save` has exactly one call site
(`application/remember/commands/open_sitting.py:109`); the port documents the aggregate as
write-once. But every read recomputes `present = sitting.visible(live)` against the live
catalog, and `Sitting.visible` documents it: *"gone ids drop out; the stored set is
unchanged."*

**Why:** The pin blocks additions, not removals. A card leaving `distill`'s catalog
mid-sitting silently leaves the draw pool, and `is_finished`/`outstanding` iterate only over
`present`, so the sitting still completes. Evidence read directly in `domain/remember/sitting.py`,
`application/remember/queries/current_card.py`, `application/remember/commands/grade_card.py:66`.

**Consequence:** A remember-local rejection record cannot live on the `Sitting` — it is
frozen and written once. Any purely local option costs a new store, not a field.

### 2026-09-11 — outbox-alone-insufficient: the outbox alone leaves remember blind — ACCEPTED

Rejection produces no `ReviewEvent`, so a rejected card's `_showing_count` stays at zero
while every graded card has at least one. `Sitting._eligible_pool` selects the
minimum-showings bucket, so the just-rejected card remains a live candidate for the very
next draw — and the only candidate once it is the last unshown card in the sitting.
`outbox_poll_interval_seconds` defaults to `1.0` (`backend/src/config/settings.py:24`), and
the next draw happens on the user's keystroke, inside that window.

**Why:** The defect is not that `distill` learns late — it is that `remember` learns nothing
at all, and its own draw rule actively favours the card just turned down.

### 2026-09-11 — rejection-as-outcome: rejection is recorded in remember's review log — ACCEPTED

The user chose a fifth variant alongside the four grades, recorded in `remember`, with the
outbox carrying a `user_audit` discard into `distill` in parallel.

**Why:** The two mechanisms do two different jobs and neither is redundant. The local record
closes the in-sitting window found above; the `distill` discard is what actually delivers
AC-17 across sittings, because `InMemoryReviewCatalog._live_cards` already excludes cards
carrying a discard (`adapters/out/in_memory/remember/review_catalog.py:37`) and
`open_sitting` builds every new sitting from that catalog.

**Consequence:** `Grade` is currently a total input to the scheduler in two places — the
`_RATINGS` map in `adapters/out/fsrs/` is exhaustive over `Grade`, and
`SchedulingReplay.replay` folds *every* stored event through `Scheduler.review`. Whatever
carries the rejection outcome, it must not reach either. Written into the body as a boundary.

### 2026-09-11 — rejection-durability: rejection is best-effort, not guaranteed — ACCEPTED

Raised against the user's own framing: choosing a fifth variant alongside the four grades
reads as importing the PRD guardrail *"A grade once given is never lost, whatever happens to
the session around it."* The outbox cannot honour that — `OutboxEnvelope.fail` sets
`EnvelopeStatus.FAILED` past `max_attempts` (`domain/shared/outbox/model.py`) and nothing
replays a dead-lettered envelope.

**Why:** The user chose best-effort deliberately rather than buying reconciliation machinery
for a prototype. Recorded as a boundary so the failure mode is a decision on the record
rather than a discovery in production.

**Consequence:** `remember`'s rejection record is explicitly *not* a fallback filter at
sitting-open. Two representations of "out of circulation" would otherwise return through the
back door, which `context/adrs/distill-domain-shape/decision.md:71` argues against. The
accepted cost is that an abandoned delivery silently returns the card, with no surface that
notices.

### 2026-09-11 — fr-014-coverage: FR-014 gets an acceptance authority — ACCEPTED

The chosen design satisfies FR-014 as a by-product, but `stories.md` filed it under
`## Uncovered Requirements` with no `AC-nn`, and the frame schema forbids a container under
an effort from minting its own requirement ids. So the frame had no legal way to state it.

**Why:** The user chose to give FR-014 an AC rather than leave it satisfied-but-untested.
`stories.md` revised to version 3 (snapshot at `stories-versions/v2-stories.md`): FR-014
joins US-09's `Realizes:` line and mints **AC-23**. Allocation is monotonic and nothing
existing was reworded, so no downstream citation was disturbed. `roadmap.md`'s S-04 slice now
reads `AC-17, AC-23`.

**Consequence:** `/bdd` will write a scenario against the user/generation-time distinction,
which means the `user_audit` reason code becomes observable behaviour rather than an internal
detail. Note the standing tension: `stories.md` originally argued FR-014 has no user payoff,
and US-09's `so that` had to be stretched to carry it.

### 2026-09-11 — reveal-gate: rejection is available only after the back is revealed — ACCEPTED

The user's reason: a card is judged as a pair. The front can be sound while the back is
corrupted, or both can be bad, so half the card is not enough to judge on. The cost — a card
whose front is visibly worthless still costs a reveal — is accepted.

**Why:** It puts rejection behind exactly the gate grading already sits behind, which
dissolves the tension raised in the previous turn. Whatever carries the outcome now has one
moment of legality rather than two, and AC-05 survives untouched: recall is still recorded as
one of four steps, and rejection is not a recall record.

**Consequence:** The gate is unenforceable in the backend, and deliberately so.
`RevealBackQuery` is read-only with no `UnitOfWork` and leaves no trace
(`application/remember/queries/reveal_back.py`), so nothing records that a back was seen. But
this is inherited, not introduced: `GradeCardCommand._guard_grade` already checks membership,
expiry, completion and presentability and never checks reveal, so AC-05's "after revealing the
back" is already a TUI-level convention. Rejection joins it at the same level and buys no new
machinery.
