## Current State

Session closed 2026-09-10. The framing is settled and lives in `frame.md`; nothing below repeats it.

**One decision left to the user, non-blocking:** the expiry horizon value. The session established how to pick it — there is no cost side to weigh, so the number answers only how long a frozen due set stays worth resuming — and left about a day as the working assumption without the user naming a figure. The PRD already files this as a non-blocking Open Question owned by the user, and it is a configuration entry rather than a design choice, so `/discover-contracts` and `/plan` can proceed on the assumed default and the number can be tuned after first use.

**Carried into `/discover-contracts` as shape questions this session deliberately did not answer:**

- Whether resumption is one convergent `POST /review-sittings` or a `GET` alongside it. A separate `GET` is only earned by a consumer that must ask without acting, and that consumer is S-03's due count, not this slice.
- What the sitting repository returns versus what the application layer evaluates. Done-ness is derived from the event log against the live catalog rather than stored as a flag, so "find the resumable sitting" cannot be a plain column filter.
- Where the outstanding count is computed. The sitting aggregate already knows its unfinished members; no DTO in `backend/src/application/remember/dto.py` carries the number.

**One thing to raise again when identity work begins,** recorded in full in the log under `sitting-uniqueness`: the uniqueness invariant is held today only by the reason for it, since no test can distinguish it from AC-11. Under per-user scoping it becomes directly observable and should be promoted to an AC on the effort then.

## Log

### 2026-09-10 — leaving-definition: what a user "leaves" is undefined and decides the whole change — OPEN

The stated fix (TUI store) is only sufficient under the narrowest reading of leaving: ESC out of the overlay while the TUI keeps running.

**Why:** `tui/src/screens/SittingOverlay.tsx:30-33` discards `sittingId` on ESC, and `tui/src/store/sitting.ts` is plain zustand state with no persistence — a repository-wide grep for `fs.`/`writeFile`/`persist` over `tui/src` returns nothing. So under a wider reading (quit Weles, come back tomorrow) a TUI-side store cannot satisfy AC-11 in principle, and the change is backend-side instead. US-05's own words — "leave a review at any point and come back to it **later**" — lean wide, but that is inference, not a settled reading.

### 2026-09-10 — resume-already-built: S-02 may add finding and expiry, not resume — OPEN

Resuming a known sitting id may already work end to end from S-01.

**Why:** The S-01 frame settled that the sitting is persisted and write-once, with all per-sitting state derived from review events scoped by `sitting_id` (`context/archive/changes/2026-09-09-remember-flow-review-session/frame-log.md:254`, `:270`). `GET /review-sittings/{sitting_id}/current-card` is already routed (`backend/src/adapters/http/remember.py:37`). S-01's frame explicitly parked exactly two things for this slice: "Expiry of a sitting, and offering an unfinished one back to the user" (`context/archive/changes/2026-09-09-remember-flow-review-session/frame.md:48`). That is the shape of the gap, and it is narrower than "add resume".

### 2026-09-10 — per-user-pinning: there is no user to pin to — OPEN

The alternative half of the stated framing ("pin a sitting per user on the backend") names a scoping key this system does not have.

**Why:** `backend/src` has no `user_id`, no auth, no request identity of any kind. The PRD's persona is "the single Weles user" and Non-Goals bar multiple devices and synchronization. The idea survives only in its de-scoped form — a global "at most one resumable sitting" invariant — which is a real design position but has to be argued as an invariant, not as a lookup index.

### 2026-09-10 — leaving-definition: leaving is wide — resume must outlive the client process — ACCEPTED

The user reads a sitting as shared state a user returns to "wherever they log in", not as view state within one running client.

**Why:** Under that reading a TUI-side store is not a candidate mechanism at all — `tui/src` persists nothing (no `fs`, no cache; zustand is process memory), so an id held there dies with the process it was held in. It also matches US-05's own "come back to it **later**" and the duck's picture of a sitting as a frozen batch that ages against a horizon (`context/duck-sessions/remember-pillar/log.md:89`) — an object with a lifetime measured in hours, not in view mounts. **Consequence:** the change is server-side; the TUI's `reset()` on ESC (`tui/src/screens/SittingOverlay.tsx:30-33`) stops being the defect and becomes correct behaviour, because the client is no longer the thing that remembers.

### 2026-09-10 — per-user-pinning: replaced by the question of what identifies a resumable sitting — OPEN

The user's answer to "there is no user" is that there will be one — auth is coming, a sitting will follow the user across logins, and a port could surface a `user_id` now even though the mechanism is undecided.

**Why:** The claim is fair about direction and the duck already anticipated it ("an environment setting in v1, **per-user later**", `context/duck-sessions/remember-pillar/log.md:90`). What it does not yet establish is that the key must exist *now*. Two costs pull against each other and neither has been measured yet:

- Minting it now buys nothing testable. A `user_id` port with one constant adapter has no second implementation to prove against, so `context/foundation/rules/contract-testing.md`'s one-contract-per-port suite would assert a constant. Every lookup keyed by it would be exercised with exactly one key, and this project has twice refused a field on that reasoning — the S-01 frame kept `showing_limit` only once a sitting could outlive the setting, and refused the frozen completion policy for the same reason (`context/archive/changes/2026-09-09-remember-flow-review-session/frame-log.md:358`).
- Not minting it risks a retrofit. But the stores are in-memory (`backend/src/adapters/out/in_memory/remember/sitting_repository.py`), so there is no persisted row to migrate; the retrofit is code, not data.

**The sharper split, and where the thread now sits:** a *lookup* parameter is cheap to add later, an *invariant* is not. "At most one resumable sitting" as a global rule is a different domain statement from "at most one per user", and that is the choice with retrofit cost — not the signature. **Supersedes:** the 2026-09-10 `per-user-pinning` entry, which argued only that no user exists today.

### 2026-09-10 — sitting-uniqueness: at most one resumable sitting, stated globally and re-scopable — ACCEPTED

The user takes the global form while naming its successor: when a second selection axis exists (topic, owner), the rule narrows to one open sitting per axis value rather than disappearing.

**Why:** It costs nothing today and answers thread 1's real question. With one selection policy ("everything due"), a second concurrent sitting would be drawn over the same due set, so uniqueness forbids only something already meaningless. Its payoff is that "which sitting is offered back?" has exactly one answer, which is what AC-11 needs and what removes a disambiguation surface from the UI.

**Two of the three justifications do not survive, and the distinction matters downstream.** The user's anti-spam reason ("does not accumulate unfinished sessions") is already bought by lazy expiry — the same correction this project made once before, when terminality was found to be oversold for exactly this reason (`context/archive/changes/2026-09-09-remember-flow-review-session/frame-log.md:73`). And "does not start new ones without finishing old" holds only if `/remember` offers no way to abandon the current sitting; with a "start fresh" branch the invariant guarantees one-at-a-time, not closure. What is left standing is findability, and that is enough.

**Consequence:** recorded under `## Boundaries`, not `## Requirements`. Under an effort a change cites `AC-nn` and never mints its own, and no AC in `stories.md` states uniqueness — so as written it is an internal mechanism serving AC-11. Promoting it to a user-visible guarantee requires a new AC on the effort.

### 2026-09-10 — per-user-pinning: the re-scoping answer weakens the case for minting a key now — OPEN

The user's own argument for the global form is that the invariant will be re-scoped later when a new axis arrives.

**Why:** That is the same retrofit `user_id`-now was proposed to avoid, accepted here without objection for the topic axis. If re-scoping the invariant is acceptable for topics, the asymmetry that makes it unacceptable for owners has not been stated. Worth noting too that the topic axis is itself a PRD Non-Goal, deferred with a reason — "a selection that ignores due-ness forces a second completion policy alongside it" (`context/efforts/remember-flow/prd.md:74`) — so it is a future the PRD deliberately holds off, not a scheduled one. **Supersedes:** the 2026-09-10 `per-user-pinning` entry that split lookup from invariant.

### 2026-09-10 — per-user-pinning: owner is a tenancy axis, not a selection axis — and that is why it is out — REJECTED

The user distinguishes the two axes correctly: topic narrows *what a sitting selects* and is optional; owner filters *everything, always*, whether or not topics ever exist. The earlier claim that re-scoping for topics and retrofitting an owner are the same retrofit was wrong.

**Why the distinction cuts against minting the key here rather than for it:** precisely because owner filters everything, it does not belong on the sitting lookup alone. `ReviewCatalog`, `SchedulingStateRepository` and `ReviewEventStore` (`backend/src/domain/remember/ports.py`) would each need it, and the cards those read come from distill, which has no ownership key either. A `user_id` present on one of those four ports and absent from the other three is worse than none: it reads as tenancy while enforcing nothing. So the honest options are a full tenancy pass across the remember ports and their upstream, or nothing — and a full pass is neither in AC-10 through AC-13 nor confined to this effort. **Consequence:** recorded in `## Boundaries` as an explicit out-of-scope statement, so the absence reads as a decision rather than an oversight when auth lands.

### 2026-09-10 — resume-gesture: silent return, no start-fresh mode — ACCEPTED

`/remember` against an unexpired open sitting drops the user straight back into it, showing the members that sitting has not yet finished.

**Why:** The user chose silence over an offer, with a start-fresh mode explicitly parked as a possible future. The design is coherent: membership was already frozen at open in S-01, so cards falling due mid-sitting were always excluded until it ends — silent return adds no new staleness, it only extends the window over which the existing freeze applies. The natural exit stays the intended one, finishing the batch, which is what the slice title promises. **Consequence:** the expiry horizon stops being a free parameter. It is now the only release from a batch a user has stopped wanting, so a badly chosen value is directly user-visible — a consequence the PRD's non-blocking treatment of that number was decided before.

### 2026-09-10 — resume-already-built: confirmed — the slice adds lookup and expiry, not resume — ACCEPTED

Resume by known sitting id works end to end today.

**Why:** Read rather than inferred. `CurrentCardQuery.handle` (`backend/src/application/remember/queries/current_card.py`) loads the sitting, lists its events, filters membership against the live catalog and returns `next_card` over the unfinished members — which is exactly the "only the cards this sitting has not sifted out yet" behaviour the user described, already implemented. `GradeCardCommand.handle` commits the review event and the scheduling state in one unit of work per grade (`backend/src/application/remember/commands/grade_card.py`), so grades given before leaving are durable by construction. **Consequence:** AC-10 is a criterion to cover with a test, not to build; AC-11's remaining gap is the lookup that resolves a sitting without the client supplying an id. **Supersedes:** the 2026-09-10 `resume-already-built` entry that raised this as a hypothesis.

### 2026-09-10 — resume-lookup: no stored pointer — the lookup is derived, and it lives inside opening — ACCEPTED

Nothing new records "the current sitting". Opening a review looks for a sitting that is still resumable and returns it instead of creating a second one.

**Why:** With uniqueness settled, a sitting's own state — unfinished and within the horizon — already identifies it, so a stored pointer would be a second copy of a derivable fact. That is the rule this pillar has applied four times over (`context/duck-sessions/remember-pillar/log.md:204`, on scheduler state, session disposability, expiry and progress). It also collapses two things into one mechanism: because done-ness is derived rather than flagged, the uniqueness invariant cannot be a write constraint — it can only be a guard at open, which is the same code path as the silent return.

**Consequence, and it closes the session's opening question:** `POST /review-sittings` becomes convergent — call it with a live sitting outstanding and you get that sitting back. The user's original instinct that `/remember` should be idempotent was right; only its location was wrong. It is a property of the opening command, not of a client-side store.

### 2026-09-10 — silent-versus-invisible: not being asked is not the same as not being told — OPEN

Raised while the user was weighing endpoint shapes; it is the framing question underneath them.

**Why:** `resume-gesture` settled that `/remember` does not put a choice in front of the user. It did not settle whether the response distinguishes a resumed sitting from a new one, and that difference is user-visible rather than transport detail: landing mid-batch with no marking can read as "Weles lost my place and gave me a random card", which is the loss AC-11 exists to remove. If the distinction is wanted, it constrains what opening returns, so it is settled here rather than in contract-shaping. Nothing about the endpoint count is decided in this entry — one convergent `POST` versus a `GET` alongside it stays a *how*, and a separate `GET` is only earned by a consumer that must ask without acting, which is S-03's due count and not this slice.

### 2026-09-10 — silent-versus-invisible: the return is marked and counted; the id stays internal — ACCEPTED

The user wants `/remember` landing on an existing sitting to say so, together with how many cards are left. Accepted for the marking and the count, rejected for the identifier.

**Why the count is in and needs no new AC:** AC-11 is "return to a session they left and **continue with the cards from it still outstanding**" — the count is how a user perceives that set, not a fact about it that nobody asked for. It is also genuinely absent today: no DTO in `backend/src/application/remember/dto.py` carries a remaining figure, though the sitting aggregate already computes unfinished membership internally. Unlike uniqueness, this does not need minting an AC, because it renders one that exists. Note the honest behaviour to keep in mind downstream: a card graded lowest stays unfinished, so the number holds rather than dropping — it counts outstanding members, not gradings performed.

**Why the id is out:** a UUID is not a fact a single user with at most one sitting can act on — it is debug output in a user-facing string. It also quietly restores the mental model this session removed, where the id is something a client tracks and a person might quote back. Marking the *fact* of resumption carries the whole product payoff; naming the sitting carries none of it. Recorded as an explicit out-of-scope statement so the omission reads as a decision.

**Distinction worth carrying:** statistics are a PRD Non-Goal, but this is not one. The outstanding count describes the state of the batch in front of the user, not a report over review history.

### 2026-09-10 — sitting-uniqueness: a mechanism, revisited as a promise when identity lands — ACCEPTED

Uniqueness stays in `## Boundaries`. No AC is minted on the effort for it now, and the question is deliberately left to return.

**Why, and the reason matters more than the outcome here:** the user's stated ground was avoiding the cost of amending `stories.md`. That ground on its own would justify never adding an AC to anything, so it is not the one worth recording. The one that holds is the second test: under silent return, "no second sitting was created" is observed as "I am on the card I left on", which is already AC-11's scenario — so a promise-scenario distinct from the one `/bdd` will write anyway cannot be authored today. A guarantee no test can distinguish is not yet a promise, whatever anyone intends by it.

**The user names a revisit trigger, and it is a better one than the two already on the table.** Under identity, uniqueness becomes *one open sitting per user*, and that **is** directly observable — one user's outstanding sitting must not block another's — so a scenario becomes writable without inventing a mode. Recorded alongside the two futures already named, a second selection axis (topic) and a start-fresh mode, either of which would also make the refusal visible.

**Consequence to carry into identity work:** the guarantee is until then held only by the reason for it. A future change that keeps AC-11 passing while allowing two sittings — a lookup taking the most recent, say — would break nothing any test asserts. **Supersedes:** the 2026-09-10 `sitting-uniqueness` entry, which took the invariant but left its home undecided.

### 2026-09-10 — expiry-cost: expiry loses no due card, only the expired sitting's showing counts — ACCEPTED

The user's reading is right: cards left ungraded in an expired sitting are picked up by the next one.

**Why:** `card_is_due` (`backend/src/domain/remember/scheduling_state.py:20`) answers from the card's own scheduling record, not from any sitting. A card that was due at open and never graded has an unchanged record, so it is still due and joins the new sitting. A card graded well has moved out of due-ness and correctly stays out; one graded lowest gets a due time minutes away and so returns. This is the duck's original argument for expiry being cheap — the log is the truth, so what expires is only "the batch I committed to" (`context/duck-sessions/remember-pillar/log.md:167`).

**The one thing that does not carry, worth stating because it is invisible otherwise:** showing counts are scoped by `sitting_id` (`Sitting._sitting_events`), so a card shown twice toward `showing_limit` in the expired sitting starts from zero in the new one. That is coherent — a new sitting is a new commitment — but it means expiry is not perfectly free, and the fact belongs in the frame rather than being discovered during implementation.

**A correction to how the horizon question was being framed.** Lock-in release is a consequence noticed only after silent return and no start-fresh mode were chosen; it was not expiry's original purpose. The duck's reason was staleness — a frozen set outliving the picture it was chosen against, with cards possibly discarded in distill meanwhile (`context/duck-sessions/remember-pillar/log.md:89`). Both hold now, and they pull the number in different directions, which is the useful way to put the choice.

### 2026-09-10 — expiry-cost: the cost is not merely cheap, it is not expiry's at all — ACCEPTED

Correcting the previous entry, which overstated what expiry loses.

**Why:** The user asked whether the point was that a different `sitting_id` reshuffles the draw. It does — `Sitting._draw_seed` mixes the sitting id into the seed — but that is cosmetic; presentation order is arbitrary by design. The cost named earlier was the other one: showing counts are per-sitting, and `_card_is_finished` retires a card at `showing_limit` (`backend/src/domain/remember/value_objects.py:16` — `Grade.GOOD`/`Grade.EASY` finish it outright; otherwise the count does). On re-examination that reset is **not specific to expiry**. Finish a sitting normally and a card graded lowest is due again within minutes, so the next sitting re-includes it with a fresh count in exactly the same way. `showing_limit` was never a cross-sitting guard, so expiry takes nothing that ordinary completion does not.

**Consequence, and it settles how to pick the horizon:** there is no cost side to weigh. The number answers only the staleness question — how long a frozen due set stays worth resuming — with lock-in release riding along for free. **Supersedes:** the 2026-09-10 `expiry-cost` entry, which recorded the showing-count reset as a real if small price.
