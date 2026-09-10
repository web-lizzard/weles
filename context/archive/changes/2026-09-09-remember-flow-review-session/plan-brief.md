# Review Sitting Core — Plan Brief

> Full plan: `plan.md`

## What & Why

Deliver the first review sitting end to end — open a session over everything due, present one
card at a time, reveal a back on request, take a four-step grade, and move that card's
schedule on. It is slice S-01 of `remember-flow` and the prerequisite for every other slice on
that roadmap.

## Starting Point

A closed `/discover-contracts` session put the whole remember domain and application on disk as
signatures with `...` bodies. Nothing else exists: no adapters, no HTTP router, no compose
wiring, and `fsrs` is not a dependency. The acceptance layer is already red over AC-01…AC-09.

## Desired End State

A user calls the review API, works through every due card, reveals each back, grades it one of
four ways, and sees the next-due date move — every grade permanent the moment it is taken, and
an unfinished sitting costing nothing. The full backend suite is green, including the remember
acceptance scenarios and four port contract suites.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Card identity in remember | Remember-owned twin `CardId` | Keeps the pillar boundary — the catalog adapter is the only place a distill card becomes a remember card. | Plan |
| Slice depth | Adapters + HTTP + compose | S-01 is a tracer bullet; without a route nothing is reachable. | Plan |
| Frame-derived scenarios | Tagged under existing `AC-nn` | Preserves the traceability chain to `stories.md`; a scenario tagged to no requirement tests something nobody asked for. | Plan |
| BDD driver | Real in-memory adapters, application calls | Test-double policy prefers the real adapter; today's `_FakeScheduler` proves AC-07 about itself. | Plan |
| FSRS fuzz | Global seed from the event's own facts, no lock | The only way replay reproduces `due_at` bit-for-bit; the region holds no `await`, so it is atomic against the loop. | Plan |
| Stale stamp | Treated as due; rebuilt on the grade path | One reconstruction site, and the open path never reads a date it cannot trust. | Plan |
| Foreign events | Filtered inside `Sitting` | Completeness and ordering cannot be bypassed by a caller passing `list_by_card` output. | Plan |
| Catalog source | `NoteRepository.list_all` → `list_by_note` | Distill's `CardRepository` has no `list_all`; this needs no change to distill's ports. | Plan |

## Scope

**In scope:** the sitting aggregate and its two named rules, the review log, per-card memoized
scheduling state, replay from the log, the four application flows, five in-memory adapters plus
the real `fsrs` adapter, the HTTP surface, an acceptance layer grown to the frame's
behaviours, and the four handler unit-test modules moved off their hand-rolled doubles.

**Out of scope:** AC-10…AC-22 (resume, expiry, due count, capture prompt, rejection, source
jump, capture entry), sitting expiry, scoped or timeboxed selection, any substitutable
selection or completion policy, SQL/Notion adapters, a SQL-row lock for concurrent grades
(the in-memory UoW lock is Phase 9), and the TUI.

## Architecture / Approach

Inside out. Domain rules first (they depend on nothing), then the application flows that
compose them, then the adapters satisfying their ports, then HTTP. The acceptance layer grows
at the very top so the frame's behaviours are red before any body is written, and the step
definitions move onto the real adapters at the very bottom, once those adapters exist — and
with them the four handler unit-test modules, which today hand-roll twenty doubles between
them.

```
HTTP router → command/query handlers → Sitting + SittingCompletion + seeded draw
                                     ↘ ports: ReviewCatalog · Scheduler · Clock
                                     ↘ UoW: sittings · review_events · scheduling_states
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Extend acceptance | Frame-derived scenarios under existing AC tags | A scenario that quietly imports S-02 behaviour |
| 2. Membership & due-ness | `ShowingLimit`, `contains`/`visible`, `card_is_due` | `card_is_due` gains a stamp parameter — a contract change |
| 3. Completion & ordering | `SittingCompletion`, `_eligible_pool`, seeded `next_card` | Least-shown invariant is easy to state and easy to get wrong |
| 4. Replay | `SchedulingReplay.replay` | Event ordering must be by `reviewed_at`, not insertion |
| 5. Open sitting | `OpenSittingCommand` | Nothing-due must write nothing at all |
| 6. Reveal & current | `RevealBackQuery`, `CurrentCardQuery` | Presentation must survive a reread |
| 7. Grade | `GradeCardCommand` | Guard order; event saved before memo; lock lives on the Phase 9 UoW |
| 8. Adapter stubs | Package, three repositories, UoW, clock — signatures only | A body slipping in early makes the next phase's tests vacuous |
| 9. Fill adapters & contracts | Snapshot/restore, shared asyncio.Lock, contract suites | Snapshot/restore must cover all three stores; lock must be composition-scoped |
| 10. Catalog stub | `InMemoryReviewCatalog` signature | — |
| 11. Fill catalog | `ReviewCatalog` over distill, contract suite | Discarded cards must vanish from both methods |
| 12. FSRS dep & stub | `fsrs==6.3.2` pinned, `FsrsScheduler` signature | `uv sync` must run here or the next phase cannot import |
| 13. Fill FSRS adapter | Grade mapping, seeded fuzz, repeatability test | Fuzz reproducibility is unproven until the library is installed |
| 14. HTTP & compose stubs | Four route signatures, providers, router included | — |
| 15. Fill HTTP & compose | Four routes, full wiring, route tests | `ShowingLimit` must reach only `OpenSittingCommand` |
| 16. Migrate BDD & handler tests | Doubles retired from the step module and the four handler modules | AC-07 assertion must move from multiplier to growing interval; the stale-stamp test still needs a forced stamp |

**Prerequisites:** none beyond the closed frame and contracts. Phase 12 pins `fsrs` and runs
`uv sync`; Phase 13's tests depend on it.

**Estimated effort:** large — sixteen phases, five new seams, one new runtime dependency.

**Phase shape.** Domain and application phases fill bodies into signatures the closed contract
session already wrote, so each is one phase with its own tests. That session never reached the
adapters or HTTP, so those five units are each a stubs phase (signatures, no tests) followed by
a behaviour phase (tests) — otherwise a phase's tests import symbols that do not exist and fail
on collection rather than on assertions.

## Open Risks & Assumptions

- `fsrs` is not yet installed, so its fuzz behaviour is taken from `research.md:56`. Phase 13
  either confirms the seeding approach or falls back to `enable_fuzzing=False` with the
  adapter's own `random.Random` fuzz.
- Seeding the global generator assumes the scheduler port is driven from the event-loop thread.
  A threadpool caller would need a `threading.Lock`; an `asyncio.Lock` would not help.
- A stale stamp making every card due means the first sitting after a library bump may be the
  whole backlog. Accepted — the frame caps nothing.
- Reaching completion is not the first-run path; a large first due set will not be exhausted.
- Two overlapping grades of the same in-front card both pass `next_card` until the first
  commit is visible. Phase 9 serializes that window with a shared `asyncio.Lock` on the
  in-memory UoW. A later SQL adapter maps the same window to a database lock.

## Success Criteria (Summary)

- `cd backend && uv run pytest` green, including `tests/bdd -m "remember-flow"`.
- Every remember port carries a contract suite reporting under the `in_memory` id.
- A card's `due_at` replayed from its review log equals the one the live path produced, fuzz
  included.
