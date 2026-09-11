## Current State

Session closed 2026-09-10. `frame.md` is frozen and holds everything settled; read it first.

What remains genuinely open, none of it blocking the next step:

- **Where on screen the total sits.** Deliberately left to `/plan`. The boundary fixes only that it survives an open overlay. One fact worth carrying forward: reusing `WelesBrand`'s slot inherits its eviction rule — `shouldShowWelesBrand` (`tui/src/screens/CaptureScreen.tsx:244-`) budgets it against terminal rows and drops it first as a conversation fills.
- **`stories.md` v3.** Non-divergence and the breakdown are user-facing outcomes no AC covers, so `frame.md` carries them under `## Boundaries` as design constraints and `## Requirements` cites AC-14 and AC-15 only. If acceptance authority is wanted, `/user-stories` appends AC-23 and AC-24 under US-07 and `/roadmap` widens S-03's criteria line. Both additive; neither reopens this session.
- **`scheduler-aware-finish`**, parked in `context/changes/remember-flow-scheduler-aware-finish/` behind persistence. Its own `change.md` carries the evidence; its own `/frame` recalculates from it.

Two positions this session argued for and then withdrew, recorded so they are not re-derived: the claim that the two counters could never share a screen (true of the current `app.tsx` geometry only, and that geometry is now in scope to change), and the recommendation to leave the overlay breakdown to a follow-on (no slice exists for it, and the consistency argument behind it did not hold).

## Log

### 2026-09-10 — helper-reuse: due-count reuses the existing due predicate — ACCEPTED

The user's framing — that the domain side is already there — checks out. `due_card_ids` and `card_is_due` are at `backend/src/domain/remember/scheduling_state.py:22-49`, pure, and today called only from `OpenSittingCommand` (`backend/src/application/remember/commands/open_sitting.py:75`).

**Why:** a second definition of "due" is the failure this change most easily walks into — a count that disagrees with the sitting it predicts. Reusing the predicate makes disagreement impossible by construction.

**Consequence:** whatever the count means, it inherits `card_is_due`'s semantics wholesale, including "no scheduling record means due". That inheritance is itself a question (see `due-of-never-reviewed`), not a free win.

### 2026-09-10 — read-only-path: the due count writes nothing — ACCEPTED

AC-14 says the count is available without a review session being started. Taken literally, reading the count must not mint a sitting.

**Why:** `OpenSittingCommand` is the only current path to a due set and it writes (`uow.sittings.save`, `uow.commit`). Reading a count through it would create the very session AC-14 says must not exist.

**Consequence:** the change adds a query, not a command. No unit of work commit on this path.

### 2026-09-10 — count-vs-outstanding: what the number counts during a live sitting — OPEN

Two numbers over overlapping sets can be on screen simultaneously: the global due count and a sitting's `outstanding_count`. FSRS puts a `forgot` card minutes ahead, so the global count can drop and then rise again mid-sitting.

**Why:** this is a domain-shape question, not a TUI one, and it is the part of the framing the "it's mostly TUI" reading skips over.

### 2026-09-10 — due-of-never-reviewed: whether a never-reviewed card is "due" — OPEN

`card_is_due(None, as_of, stamp)` returns `True`, so the count includes every card distill has ever produced and nobody has graded.

**Why:** the sitting inherits this and it is correct there — a new card should be reviewable. Whether the same is true of a number the user reads to decide whether to sit down is a separate judgement.

### 2026-09-10 — count-surface: where the number appears — OPEN

AC-14 constrains only that no session is started. The PRD's open question 4 assumes visibility during a capture conversation.

**Why:** S-07 depends on S-03, so where this number lives shapes whether the post-capture prompt is duplicative — the PRD flags exactly that.

### 2026-09-10 — count-vs-outstanding: the two numbers must never contradict — ACCEPTED

The user's call: the due count and a sitting's `outstanding_count` must not disagree where both are visible. Recorded as a boundary in `frame.md`.

**Why:** two numbers over the same-looking subject, differing on screen, is the failure that makes a glanceable count worse than no count — the user stops trusting either.

**Consequence:** the *goal* is settled; the mechanism is not, and is now the session's live thread.

### 2026-09-10 — outstanding-as-source: making the count delegate to Sitting.outstanding — REJECTED

The proposed mechanism — have the query load the sitting and report `Sitting.outstanding`, keeping the calculation inside that aggregate — does not hold. The two sets diverge in both directions, structurally:

- `Sitting.card_ids` is frozen at `open` (`domain/remember/sitting.py:40`), so anything ripening after `opened_at` is globally due and permanently outside the sitting.
- `FINISHING_GRADES = {GOOD, EASY}` (`domain/remember/value_objects.py:20`), so a `hard` card stays in `outstanding` and keeps being re-drawn — while FSRS pushes its `due_at` forward by minutes (learning) to days (mature). The sitting owes it; the schedule says not for days.
- `_card_is_finished` retires a card at `showing_limit` showings without a Good (`sitting.py:135`), dropping it from `outstanding` while it may still read due.

**Why:** `outstanding` answers "what does this sitting still owe me", `due` answers "what does the schedule say is ripe". One cannot delegate to the other without silently answering a different question.

**Consequence:** the "keep it in that aggregate" rationale also does not apply — `due_card_ids` is a module function over `SchedulingState`, not a `Sitting` method. There is no single aggregate that owns both, so the query combines two domain surfaces whichever way this goes. Three positions (sitting-wins-while-offered / schedule-wins-always / union) are now in `## Current State` awaiting a choice.

### 2026-09-10 — consistency-has-no-ac: non-divergence is covered by no acceptance criterion — OPEN

Neither AC-14 nor AC-15 mentions consistency with a sitting. Under `references/frame-schema.md`, a change beneath an effort may only cite `AC-nn` and never mint `FR-nn`, so this guarantee has no acceptance authority and the coverage rule leaves `/bdd` nothing to tag.

**Why:** a constraint that reaches `/plan` but not `/bdd` is a constraint nothing verifies. Either it stays a design boundary or `stories.md` gains an AC under US-07.

### 2026-09-10 — scheduler-aware-finish: a card pushed beyond the sitting's reach should stop being re-drawn — ACCEPTED

Raised by the user against the boundary that barred touching `Sitting`. It holds on S-01's own terms, independent of counting.

Measured FSRS defaults: `learning_steps = (1min, 10min)`, `relearning_steps = (10min,)`. `forgot`, and `hard` on a card still in learning, land minutes out — re-showing them in this sitting agrees with the scheduler. `hard` on a **mature** card lands days out, yet `_card_is_finished` (`domain/remember/sitting.py:132-139`) keeps it outstanding and `_eligible_pool` keeps re-drawing it until `showing_limit`. The user re-grades, FSRS says days again, it returns again.

**Why:** the aggregate is overruling the scheduler on the one grade where the scheduler has actually spoken. `FINISHING_GRADES` and `showing_limit` are the only two arms today, and neither can express "the schedule has moved this past today".

**Consequence:** the rule is `due_at > opened_at + resume_horizon` — the sitting's own reach, both terms already snapshotted on the aggregate. Not `due_at > now`, which would retire a `forgot` card a second after grading and break AC-09.

### 2026-09-10 — scheduler-aware-finish: it does not resolve count-vs-outstanding — REJECTED as a convergence mechanism

Accepted above as a defect fix; rejected as an answer to the counting question that motivated reaching for it.

A `forgot` card is due in 1 minute — inside `opened_at + resume_horizon`, so still outstanding, and `due_at > now`, so not globally due. `outstanding ⊄ due` no matter what the third arm says. AC-09 *is* that gap: it states that the sitting owes a card the schedule does not yet.

**Why:** the divergence the horizon test removes is the *large* one (days, mature `hard`); the one it cannot remove is required by a shipped AC. Shrinking days to minutes is worth having and is not the same as convergence.

**Consequence:** positions (a) / (b) / (c) in `## Current State` are still owed a choice.

### 2026-09-10 — sitting-change-in-scope: whether S-03 carries the aggregate change — OPEN

`frame.md` bars changing what `Sitting` counts as finished. `scheduler-aware-finish` challenges that bar.

Cost if pulled in: `outstanding` / `is_finished` / `next_card` are pure over ids + events today and would take a `Mapping[CardId, SchedulingState]`, rippling through 13 call sites in `open_sitting.py`, `grade_card.py`, `current_card.py`, plus `tests/unit/remember/test_sitting.py` and the mutant tree — a behaviour change to two archived slices (S-01, S-02), reached for by a counting slice.

**Why:** the defect is real and the fix is cheap to describe, but S-03's payoff (AC-14, AC-15) does not depend on it — the counting decision stands either way.

### 2026-09-10 — sitting-change-in-scope: the mutant tree is not part of the ripple — ACCEPTED

Correcting the cost estimate in the earlier `sitting-change-in-scope` entry (2026-09-10), which counted `backend/mutants/` among the files a scheduler-aware `_card_is_finished` would touch.

`backend/mutants/` is gitignored (`.gitignore:17`) — a generated mutmut mirror, regenerated per run, never edited by hand.

**Why:** the estimate is what the scope decision is being made on, and it overstated the blast radius.

**Consequence:** the real ripple is 13 call-site lines across `open_sitting.py`, `grade_card.py`, `current_card.py`, plus `tests/unit/remember/test_sitting.py`. Smaller than stated, which weakens the case for keeping the change out of S-03 on cost grounds alone.

### 2026-09-10 — scheduler-aware-finish: the defect is real but dormant — ACCEPTED

Measured FSRS defaults put `learning_steps = (1min, 10min)`. A card with no review history graded `hard` therefore lands minutes out, inside any sitting — the current behaviour is correct for it. The days-out case requires a card in Review state, reached only by a prior Good or Easy.

**Why:** it bounds the urgency. On an in-memory prototype, no card carries review history across a restart, so the defect currently bites nothing.

**Consequence:** parking is defensible on evidence rather than on avoidance — but a park with no trigger is deferral in disguise. The trigger would be persistence: the first store that survives a restart is when mature cards start existing.

### 2026-09-10 — off-roadmap-under-effort: a change under an effort but off its roadmap has no precedent — REJECTED

Considered as a home for `scheduler-aware-finish`: keep `effort_id: remember-flow` but skip the roadmap.

Every archived change carrying `effort_id` also maps to a roadmap slice — `capture-flow-coverage-wrapup` is S-02 and `capture-flow-tag-dedup` is S-05 on `context/efforts/capture-flow/roadmap.md`, despite neither carrying `slice_ref` in its own frontmatter. That missing field is bookkeeping drift from before the field existed, not evidence of an off-roadmap shape.

**Why:** inventing a third relation shape to avoid a `stories.md` revision would trade a visible cost for an invisible one — a change under an effort that the effort's done-picture cannot see.

**Consequence:** the real choice is Route A (new slice, needs an AC) or Route B (standalone, `origin`-linked, mints its own `FR-01`), or parking.

### 2026-09-10 — scheduler-aware-finish: parked behind persistence, with a container to hold the findings — PARKED

User's call: not now, but yes once a real store is wired — "jutro tak, bo będziemy podpinać bazę". The trigger proposed in the previous entry is confirmed as the actual one, not a face-saving condition.

**Why:** the defect only bites cards in Review state, reachable only through a prior Good or Easy, and on an in-memory store no card carries review history across a restart. Persistence is precisely when mature cards begin to exist, so the trigger and the bite arrive together.

**Consequence:** Route B — a standalone change, `origin: remember-flow-due-count`, no `effort_id`, opened now and left unstarted, carrying a synthesis in its `change.md` so its own future `/frame` recalculates from evidence rather than from memory. Route A is declined for now: it would force a `stories.md` v3 today for work that starts later.

### 2026-09-10 — scheduler-aware-finish: container opened, thread closed here — ACCEPTED

`context/changes/remember-flow-scheduler-aware-finish/` created via `/new-container` (commit `27fb785`): `origin: remember-flow-due-count`, no `effort_id`, `status: new`. Its `## Notes` carry the defect, the candidate rule, the park trigger, the blast radius, and the missing-AC problem — evidence for a future `/frame` to recalculate from, explicitly not a design to adopt.

**Why:** the user asked for the findings to survive outside this session's log. A parked decision readable only in a `frame-log.md` that will archive with its change is a decision that gets lost.

**Consequence:** `frame.md`'s out-of-scope now names the container instead of merely barring the aggregate. Parking it also sharpens the count decision — until persistence lands, a mature `hard` card keeps a days-out `due_at` while staying `outstanding`, so option (b) can diverge by days for the whole duration of the park.

### 2026-09-10 — split-counters: two named counters instead of one reconciled number — OPEN

User's proposal, raised against the (a)/(b)/(c) trilemma rather than from inside it: have the DTO compute counters per category — repeat-showings such as `hard` in their own count — so both truths are shown and the right counter moves, instead of one global number absorbing everything.

It is stronger than the three options it replaces. Each of those assumed a single number, which forced it to answer only one of the two live questions ("what does the schedule say is ripe" / "what does this sitting still owe me"). Two named counters answer both, and satisfy the non-divergence boundary by a different route: numbers that no longer claim the same thing cannot contradict.

**Why it stays OPEN rather than ACCEPTED:** four things are unpinned — disjointness and the tie-break for a card that is both outstanding and due; where the partition is computed (the timing instinct is right, the DTO-assembly placement is not — three sites, `open_sitting.py:61,85`, `grade_card.py:124`, `current_card.py:43`, would each carry the same set arithmetic); confirmation that the repeat counter is `0` outside a sitting so AC-14/AC-15 stay intact; and whether both counters travel together or only the due one reaches global chrome — the latter would make this close to option (b) with honest labels.

**Consequence:** if accepted, `frame.md`'s boundary is rephrased from "must never contradict" to "each number names the set it counts", and the change grows a domain partition function plus additive defaulted fields on `PresentedCardDTO` and `GradeAppliedDTO`. That reach into shipped S-01/S-02 surface is the same ground on which `scheduler-aware-finish` was parked, and the two should be judged consistently.

### 2026-09-10 — split-counters: a total plus a breakdown within it, not addends beside it — ACCEPTED

The user's shape for item 1: one main counter of how many cards, plus sub-counters.

**Why:** it disposes of the double-count problem that made disjointness a question. A card that is both `outstanding` and `due` is counted once in the total; the sub-counters describe a subset of that total rather than adding to it, so no arithmetic a user performs on the display can be wrong.

**Consequence:** the non-divergence boundary is satisfied. `frame.md` is rephrased from "must never contradict" to "each number names the set it counts". The main counter's meaning still shifts between sitting and no-sitting — the union inside, `len(due)` outside — which is option (c)'s readability cost, inherited rather than solved.

### 2026-09-10 — breakdown-axis: breaking the total down by grade — REJECTED

Proposed as the sub-counter axis. Rejected on three grounds:

- `FINISHING_GRADES = {GOOD, EASY}` (`domain/remember/value_objects.py:20`) — a good- or easy-graded card is finished in the sitting, so two of the four buckets would count *done* cards inside a decomposition of a *waiting* number.
- Every grade bucket is empty outside a sitting, which is where AC-14 lives; the breakdown would appear only inside `SittingOverlay`, collapsing (d) toward option (b).
- A card shown repeatedly has no single grade — the axis means "most recent grade in this sitting" and needs a further gradeless bucket for cards not yet shown.

**Why:** the axis that carries information is *why a card is waiting* — not yet seen, seen and still owed, ripe but outside this sitting. Grade proxies only the middle bucket, lossily.

**Consequence:** the shape from `split-counters` stands; only the axis is sent back.

### 2026-09-10 — partition-placement: a pure domain function, neither aggregate state nor aggregate method — ACCEPTED

The user's read — that storing the number on the aggregate buys nothing since the aggregate must be fetched anyway — lands in the right place. Strengthening the reason: `outstanding_count` is derived per call and never persisted (`open_sitting.py:61,85`, `grade_card.py:124`, `current_card.py:43`), so a stored counter would be denormalized state free to drift from the event log.

**Why:** the real question was which module derives it, not store-versus-derive. It cannot be a `Sitting` method either — the partition needs `Sitting` and `SchedulingState` together, so the aggregate would have to accept scheduling state as a parameter, which is exactly the coupling parked as `scheduler-aware-finish`.

**Consequence:** one pure domain function over `(sitting, sitting_events, states, live_ids, as_of, stamp) -> partition`, beside `due_card_ids` in `domain/remember/scheduling_state.py` or its own module; the three handlers call it once and project. Precedent for both shapes already exists in this domain — `due_card_ids` as a module function, `SchedulingReplay` as a domain service class.

### 2026-09-10 — breakdown-axis: why a card is waiting — ACCEPTED

Supersedes the grade axis rejected earlier today. Buckets: not yet seen · seen and still owed · ripe but outside this sitting.

**Why:** it carries the information a user acts on, and unlike grade it has no bucket that counts finished cards and no undefined value for a card never shown.

**Consequence:** the third label has no referent outside a sitting, so the partition is defined to put every due card in *not yet seen* when no sitting is live — main equals that bucket, the others `0`, and the display condition is "render the breakdown when a non-first bucket is non-zero".

### 2026-09-10 — due-of-never-reviewed: the count stays equal to the scheduler — ACCEPTED

A card with no scheduling record counts as due, exactly as `card_is_due(None, …)` has it (`domain/remember/scheduling_state.py:22-30`). The user-facing number is not narrowed below the scheduler's own reading.

**Why:** narrowing it would be the second definition of "due" that `helper-reuse` was accepted to prevent — the count would disagree with the sitting it predicts.

**Consequence:** right after a distill run the main counter equals every live card. Under the accepted axis these all land in *not yet seen*, which is at least an honest label for them.

### 2026-09-10 — partition-api-shape: every bucket always returned, zeros included — ACCEPTED

The API returns the full partition on every read, with `0` for buckets that do not apply; the TUI conditions on display rather than on presence. Closes item 3.

**Why:** a stable response shape keeps the generated client (`tui/src/api/generated/schema.d.ts`) free of optional-field branching, and puts the "is this worth showing" judgement in the surface that knows the layout.

### 2026-09-10 — counter-colocation: the two numbers cannot share a screen — ACCEPTED

`SittingOverlay` renders `position="absolute"` at `top={0} left={0}`, `width={columns} height={rows}`, `backgroundColor="black"` over `CaptureScreen` (`tui/src/app.tsx`). It fully occludes the capture screen.

**Why:** this corrects the objection logged against option (b) earlier today, which asserted that layout alone would place both numbers on screen together. It would not.

**Consequence:** the non-divergence boundary is weaker than argued — the available contradiction is sequential (chrome 15 → overlay 3 → chrome 15), not simultaneous. (d)'s justification shifts from preventing an on-screen contradiction to explaining the jump. Placement settles cheaply: main counter in global chrome where AC-14 and AC-15 live, breakdown inside the overlay.

### 2026-09-10 — overlay-breakdown-in-scope: whether S-03 builds the overlay breakdown — OPEN

AC-14 and AC-15 are satisfied by the main counter in chrome alone. The breakdown renders only inside `SittingOverlay`, which already displays `outstandingCount` (`tui/src/screens/SittingOverlay.tsx:27`) and is owned by S-01/S-02.

**Why:** third instance of the same question — how far a counting slice may reach into shipped slices. `scheduler-aware-finish` was parked on it; the DTO fields were waved through as additive and defaulted; this one is undecided, and consistency across the three is worth more than any single call.

### 2026-09-10 — overlay-breakdown-in-scope: S-03 carries the breakdown — ACCEPTED

Supersedes this session's own recommendation, one turn earlier, to leave the overlay breakdown to a follow-on.

The user asked which slice would carry it. None does: `remember-flow`'s roadmap holds S-04 (AC-17), S-05 (AC-18–20), S-06 (AC-21–22) and S-07 (AC-16), and none presents a breakdown in the sitting overlay. A follow-on would therefore be a third container spawned from this one session, holding work with no acceptance criterion and no trigger.

**Why:** the consistency argument behind the earlier recommendation does not hold. `scheduler-aware-finish` was parked because it changes what a shipped aggregate *does*, with a 13-call-site signature ripple and a real trigger. The breakdown changes no behaviour — it renders fields the DTO already carries, in a component that already renders `outstandingCount` (`tui/src/screens/SittingOverlay.tsx:27`). The two were matched on the phrase "reaches into a shipped slice" rather than on their content.

**Consequence:** S-03 ships the partition function, the main counter in chrome, and the overlay breakdown. No further container is opened from this session.

### 2026-09-10 — consistency-has-no-ac: one `stories.md` v3 covers both gaps — OPEN

Two open items want the same file: non-divergence has no AC, and a second visible counter has no AC. Both are user-facing outcomes S-03 will ship.

`stories.md` already versions additively — v2 appended US-12 with AC-21 and AC-22 while leaving AC-01–AC-20 untouched — so v3 appending AC-23 and AC-24 under US-07 is the established move rather than a new mechanism. Highest existing criterion is AC-22.

**Why:** without it S-03 ships two visible behaviours that `/bdd` cannot tag, and `frame.md` cannot record them at all — under an effort it may only cite `AC-nn`, never mint `FR-nn`.

**Consequence if accepted:** `/roadmap` widens S-03's `Acceptance criteria` line from `AC-14, AC-15`; `frame.md`'s `## Requirements` cites all four.

### 2026-09-10 — counter-colocation: a persistent header re-arms simultaneous visibility — ACCEPTED

Supersedes the entry earlier today that recorded the two numbers as unable to share a screen. That was true of the current `app.tsx` geometry, not of the design — and the user proposes changing exactly that geometry, shifting the overlay down so a header survives underneath it.

**Why:** the non-divergence boundary is therefore live again, not weakened. (d) already carries it: counters over named sets cannot contradict, whether or not they are visible together.

**Consequence:** `frame.md` takes the shell change in scope — a number required to keep up "while Weles is open" cannot live on a surface that gets occluded. The change is not sitting-specific: `NoteListOverlay` shares the absolute full-screen pattern, and `test/app.test.tsx`, `test/noteListOverlay.test.tsx`, `test/sittingOverlay.test.tsx` all rest on the current geometry.

### 2026-09-10 — counter-home: the Weles header is the least stable chrome in the app — OPEN

The proposed home is where `WelesBrand` renders. It is conditional: `{showBrand && ...}` (`tui/src/screens/CaptureScreen.tsx:87`), with `shouldShowWelesBrand` (`:244-`) budgeting it against `stdout.rows` minus the input block, topic, error, banner, draft and approval receipt blocks.

**Why:** it is the first element dropped as a conversation fills the terminal — exactly when AC-15's "while Weles is open" carries the most weight. A counter there vanishes when it is most needed.

**Consequence:** the counter needs a reserved row of its own, or a different home. Reusing the brand's slot inherits its eviction rule.

### 2026-09-10 — refresh-causes: one read produces every number shown together — ACCEPTED

Four causes move the number: time crossing a `due_at`; distill adding live cards; grading inside a sitting; a sitting opening, finishing, or passing `resume_horizon`. The TUI originates grading and opening, and can observe neither time nor distill.

The trap is two update paths for numbers that must agree — a polled header beside an overlay updated from `GradeAppliedDTO` disagrees between ticks, invisibly under today's layout and visibly under the proposed one.

**Why:** temporal divergence is the same failure as semantic divergence to a reader; the boundary does not distinguish them.

**Consequence:** every remember response carries the full partition, so one interaction refreshes every number from one computation, and polling covers only time and distill. Mechanism — interval, SSE, or otherwise — is `/plan`'s; `useNotesPolling` with `notesStore.startPolling` is the general precedent, while `api/stream.ts` is SSE hand-declared for the messages route only.

### 2026-09-10 — session-close: framing confirmed in part, reframed in part — ACCEPTED

Closed on the user's instruction. The opening framing — "mostly a query, the helper is already in the remember domain, the rest is TUI" — held on its first clause and not its last.

Confirmed: `due_card_ids` / `card_is_due` are real, reused rather than duplicated, and the path stays read-only.

Reframed: "the rest is TUI" covered three domain decisions — what the number means while a sitting is live, where the partition is derived, and that one number cannot answer both of the questions in play. The change ships a domain partition function, a total plus a why-it-waits breakdown, a shell change that keeps the total visible, and additive defaulted DTO fields.

**Why:** a session that confirms half a framing and reframes the other half is the ordinary outcome; recording which half is which is what makes it useful to `/plan`.

**Consequence:** two by-products. `context/changes/remember-flow-scheduler-aware-finish/` holds a real S-01 defect parked behind persistence. `stories.md` v3 is available but not required — the two uncovered outcomes live as design constraints in `frame.md` instead.
