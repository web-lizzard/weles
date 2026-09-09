---
date: 2026-09-09T14:46:00+02:00
topic: "Public interface of the py-fsrs / fsrs Python scheduler"
topic_slug: null
container_id: remember-flow
tags: [research, py-fsrs, fsrs, remember]
last_updated: 2026-09-09
---

# Research: Public interface of the py-fsrs / fsrs Python scheduler

## Research Question

Zrób dla mnie research aby określić interfejs paczki py-fsrs

## Summary

The published package is **`fsrs` 6.3.2**, not `py-fsrs`. Install with `pip install fsrs`; import `from fsrs import Scheduler, Card, Rating, ReviewLog, State`. The review loop is `card, review_log = scheduler.review_card(card, rating, review_datetime=...)`. A brand-new card is `Card()`: `State.Learning`, due immediately in UTC. Persist algorithm state with `Card.to_dict()` / `to_json()`. Default `enable_fuzzing=True` makes Review-state intervals ≥ 2.5 days non-deterministic. Parameter optimization lives in optional `fsrs[optimizer]` and is a remember-flow non-goal.

This repository has not added the dependency or a remember domain yet. Duck and ADR already require: the scheduling port belongs to remember, `py-fsrs` is a real in-process adapter (no fake), and the domain holds an opaque `scheduler_state` plus an indexable `due_at` outside that blob.

## Findings

### Package name and version

- PyPI JSON names the project `"fsrs"` at `"version":"6.3.2"`. There is no `py-fsrs` project on PyPI. The GitHub repository remains `open-spaced-repetition/py-fsrs`.
- Git tag `v6.3.2` matches PyPI. GitHub Releases “latest” may still list `v6.3.1`.
- The workspace cannot `import fsrs`; `backend/pyproject.toml` does not list `fsrs` or `py-fsrs`.
- License: MIT.

### Public surface (v6.3.2)

Package `__all__`: `Scheduler`, `Card`, `Rating`, `ReviewLog`, `State`, `Optimizer` (lazy; requires `pip install "fsrs[optimizer]"`).

**`Rating` (`IntEnum`)**: `Again=1`, `Hard=2`, `Good=3`, `Easy=4`. README: Again means “forgot the card”.

**`State` (`IntEnum`)**: `Learning=1`, `Review=2`, `Relearning=3`. There is no `State.New` (removed in v4.0.0; new cards start in Learning).

**`Card`**: `card_id` (UTC epoch milliseconds if omitted), `state=Learning`, `step=0` when Learning, `stability=None`, `difficulty=None`, `due=now(UTC)`, `last_review=None`. README: all new cards are due immediately. Methods: `to_dict` / `from_dict` / `to_json` / `from_json`.

**`Scheduler`**: `parameters` (21 FSRS-6 weights, `DEFAULT_PARAMETERS`, decay `0.1542`), `desired_retention=0.9`, `learning_steps=(1 min, 10 min)`, `relearning_steps=(10 min,)`, `maximum_interval=36500`, `enable_fuzzing=True`.

**`review_card(card, rating, review_datetime=None, review_duration=None) -> tuple[Card, ReviewLog]`**: shallow-copies the card (does not mutate the input). Sets `due = review_datetime + next_interval` and `last_review = review_datetime`. `review_datetime` must be timezone-aware UTC or it raises `ValueError`. Persist the **returned** `Card`.

**`ReviewLog`**: `card_id`, `rating`, `review_datetime`, `review_duration`. This is the library’s per-review trace, not Weles’ domain `ReviewLog`.

**`get_card_retrievability(card, current_datetime=None) -> float`**: not required for a v1 review sitting.

**`reschedule_card` / `Optimizer`**: not required for a single review. Optimizer needs extra deps and a large log; remember-flow parks parameter optimization.

Serialization uses ISO datetimes. README: “Py-FSRS uses UTC only.”

### Behaviour that remember must wrap

- **Lowest grade / same sitting:** `Rating.Again` in Learning or Relearning resets `step` to `0` and uses the first learning/relearning step (defaults 1 min / 10 min). In Review with default `relearning_steps`, Again lapses into Relearning at step 0. That short interval is how “comes back in the same sitting” falls out of FSRS; the library does not own a session queue.
- **Fuzz:** applied only when the card’s state **after** the review is `Review` and the interval is ≥ 2.5 days (`random()`). Learning/relearning minute-steps stay deterministic. Tests should use `Scheduler(enable_fuzzing=False)` and an explicit UTC `review_datetime`.
- **New Weles card:** distill `Card` has no scheduling fields. Remember wraps lazily: constructing `fsrs.Card()` is FSRS’s “never scheduled” (due now, Learning, no stability/difficulty).
- **Opaque blob vs `due_at`:** `Card.to_dict()` is the natural `scheduler_state`. That dict **also contains `due`**. Duck requires `due_at` as a real domain field **outside** the blob; the adapter copies `card.due` onto `due_at` and the domain never reads the blob.
- **Grade mapping:** identity onto FSRS’s four ratings; product vocabulary is forgot / hard / good / easy. `forgot` → `Rating.Again`. The mapping is a domain-owned seam.
- **Version stamp:** with parameters fixed at library defaults, a library bump is the v1 invalidator of memoized state. Pin `fsrs==6.3.2` and stamp algorithm/parameter version on `ReviewItem`. Optionally persist `Scheduler.to_dict()` if defaults are ever customized.
- **Do not follow v3 tutorials:** v4 renamed `FSRS` → `Scheduler` and `repeat` → `review_card`, dropped `elapsed_days` / `reps` / `lapses` / `State.New`. v6 moved to 21 weights and `Scheduler.get_card_retrievability`.

### Minimal adapter wrap

```text
Scheduler()  # v1: library defaults; tests: enable_fuzzing=False
Card()                    # first encounter
Card.from_dict(blob)      # later reviews
new_card, fsrs_log = scheduler.review_card(card, Rating.*, review_datetime=utc)
persist new_card.to_dict(); expose new_card.due as due_at
```

The remember domain must not import `fsrs`. `Optimizer` and `reschedule_card` stay out of v1.

## Code References

- `backend/src/domain/distill/card.py:15-22` — distill `Card` has no scheduling fields
- `backend/pyproject.toml:6-14` — `fsrs` / `py-fsrs` not a backend dependency
- `context/adrs/distill-domain-shape/decision.md:108-110` — no scheduling port in distill; remember wraps a card lazily
- `context/duck-sessions/remember-pillar/log.md:109-111` — real `py-fsrs` adapter, no in-memory fake
- `context/duck-sessions/remember-pillar/log.md:24-25` — `ReviewItem` holds `due_at` plus opaque `scheduler_state`
- `context/duck-sessions/remember-pillar/log.md:128-129` — `due_at` stays outside the opaque blob
- `context/duck-sessions/remember-pillar/log.md:121-123` — grade vocabulary is a domain seam mapped onto FSRS ratings
- `context/duck-sessions/remember-pillar/log.md:139-141` — parameter optimization parked; fixed FSRS defaults
- `context/efforts/remember-flow/prd.md:43` — four-step scale forgot / hard / good / easy
- `context/efforts/remember-flow/prd.md:77` — FSRS parameter optimization is a non-goal

## External References

- <https://pypi.org/pypi/fsrs/json> — project name `fsrs`, version `6.3.2`
- <https://pypi.org/project/fsrs/6.3.2/> — install page for the published package
- <https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/README.md> — `pip install fsrs`, UTC-only, `review_card`, Rating/State, JSON helpers
- <https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/fsrs/__init__.py> — public `__all__`
- <https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/fsrs/card.py> — `Card` fields, defaults, `to_dict` / `from_dict`
- <https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/fsrs/scheduler.py> — `Scheduler.__init__`, `review_card`, fuzz, UTC `ValueError`
- <https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/fsrs/rating.py> — `Again=1` … `Easy=4`
- <https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/fsrs/state.py> — `Learning` / `Review` / `Relearning`
- <https://github.com/open-spaced-repetition/py-fsrs/blob/v6.3.2/fsrs/review_log.py> — library `ReviewLog` fields
- <https://github.com/open-spaced-repetition/py-fsrs/releases/tag/v4.0.0> — `Scheduler` / `review_card`, no `State.New`, Card attribute change
- <https://github.com/open-spaced-repetition/py-fsrs/releases/tag/v6.0.0> — FSRS-6, 21 parameters
- <https://open-spaced-repetition.github.io/py-fsrs> — generated API reference
- <https://raw.githubusercontent.com/open-spaced-repetition/py-fsrs/main/LICENSE> — MIT License

## Open Questions

- Whether v1 disables fuzz in the production adapter (repeatable `due_at`) or only in tests.
- Whether FSRS `card_id` (epoch ms plus a 1 ms sleep on construct) is ignored in favour of Weles `CardId` and left only inside the blob.
- Whether the library `ReviewLog` is persisted at all, given remember already plans its own review log.
