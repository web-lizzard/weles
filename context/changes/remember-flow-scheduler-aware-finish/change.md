---
change_id: remember-flow-scheduler-aware-finish
title: A card the schedule has moved beyond this sitting stops being re-drawn in it
status: new
created: 2026-09-10
updated: 2026-09-10
archived_at: null
origin: remember-flow-due-count
---

## Notes

Parked defect, surfaced by the `/frame` session on `remember-flow-due-count` and deliberately not built there. Findings below are evidence, not a design — a future `/frame` on this container should recalculate from them rather than adopt them.

**The defect.** `Sitting._card_is_finished` (`backend/src/domain/remember/sitting.py:132-139`) has exactly two arms: a grade in `FINISHING_GRADES` (`= {GOOD, EASY}`, `domain/remember/value_objects.py:20`), or `showing_count >= showing_limit`. It never reads scheduling state — `Sitting` is pure over `card_ids` + events + its two snapshotted limits. So a card graded `hard` stays in `outstanding` and keeps being re-drawn by `_eligible_pool`, while FSRS has already pushed its `due_at` forward. The user re-grades `hard`, the scheduler says the same thing again, the card returns again, until `showing_limit`. The aggregate overrules the scheduler on the one grade where the scheduler has actually spoken.

**Candidate rule.** Finished when `due_at > opened_at + resume_horizon` — the sitting's own reach. Both terms are already snapshotted on the aggregate, so no new environment reaches it. Not `due_at > now`, which would retire a `forgot` card a second after grading and break AC-09 outright.

**Why it is parked, and the trigger.** Measured FSRS defaults: `learning_steps = (1min, 10min)`, `relearning_steps = (10min,)`. A card with no review history graded `hard` lands minutes out — inside any sitting, so today's behaviour is correct for it. The days-out case needs a card in Review state, reached only through a prior Good or Easy. On the current in-memory store no card carries review history across a restart, so the defect bites nothing yet. **The trigger is persistence:** the first store that survives a restart is when mature cards begin to exist.

**What this is not.** It is not the fix for the due-count question that surfaced it. A `forgot` card is due in ~1 minute: inside the horizon so still `outstanding`, and `due_at > now` so not globally due. `outstanding ⊄ due` regardless of any third arm, because AC-09 *is* that residual gap — it states that the sitting owes a card the schedule does not yet. The rule shrinks the divergence from days to minutes; it cannot close it.

**Blast radius.** `Sitting.outstanding` / `is_finished` / `next_card` are pure over ids + events today and would take a `Mapping[CardId, SchedulingState]` — 13 call-site lines across `application/remember/commands/open_sitting.py`, `commands/grade_card.py`, `queries/current_card.py`, plus `tests/unit/remember/test_sitting.py`. `backend/mutants/` is a generated mutmut mirror (`.gitignore:17`), not part of the ripple.

**Acceptance authority is missing.** No AC in `context/efforts/remember-flow/stories.md` covers this; AC-09 covers only that a lowest-graded card returns. Deliberately opened standalone (`origin`, no `effort_id`) so its own frame may mint `FR-01` rather than force a `stories.md` v3 today. Promoting it to a `remember-flow` roadmap slice later remains open — every archived change carrying `effort_id` also maps to a slice, so "under the effort but off the roadmap" is not an available shape.

Session record: `context/changes/remember-flow-due-count/frame-log.md`, idea-ids `scheduler-aware-finish`, `off-roadmap-under-effort`, `sitting-change-in-scope`.
