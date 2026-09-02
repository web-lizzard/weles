## Current State

Second pass at **Distill**, the middle pillar of `capture → distill → remember`. Opened 2026-09-02. Several structural questions are now settled; the remaining ones are named below.

**Settled so far:**
- **Notion is de-scoped from this design.** The prototype is entirely in-memory per `InMemoryFirst`, so a Notion publish branch has nothing to prove yet. `backend-stack`'s "notes go to Notion" is not reversed — publishing returns later as one more output adapter behind the same port, picking up whatever note version is current at that point.
- **Distill owns a note record with its content.** Originally justified by "Notion is a poor query store"; with Notion de-scoped, the remaining justification is module isolation — distill works from the `note_approved` snapshot rather than reaching into capture's repositories. The content arrives free in that snapshot.
- **Cards are generated from the note only**, never the session transcript. The user's principle: it is honest to make cards from knowledge already grounded and endorsed. Same line as `overview-thougts`' `approval-policy`. If quality proves poor, the escape hatch is a **new envelope version** carrying a richer payload, not a cross-module read into capture — preserving the isolation `outbox-shared` bought with snapshot payloads.
- **`GET /_outbox` is an ops endpoint**, not the TUI's status source. Distill's status is a property of the distill *process*.
- **Regeneration of cards is wanted** — not in the first cut, but explicitly expected. This is why status wants a per-run record rather than a single field on the note.
- **TUI shell is an overlay**, not a screen swap. A command opens over the capture view rather than replacing it, so an in-flight capture session survives by construction.
- **Navigation is selection-addressed**: `/notes` → list → Enter → note → a shortcut/command into its cards. `<note-id>` as a command argument is an alternative path, never the default gesture.

- **Distill owns the note; remember asks it for changes.** Consistent with how capture already hands off to distill. The note does not move to a home outside the pillars — that option was considered and set aside as a speculative restructure.
- **Notes are born only in capture.** Remember does not author notes; it can *open capture mode*, and the ordinary capture → approve → `note_approved` path runs from there. One birth path, so `note_approved` stays distill's only input.
- **No immutability invariant on distill's note.** The prototype builds no amendment and no regeneration, but deliberately does not give the note record a "content never changes after save" invariant, and a distillation run points at a note version even while that version is always 1. One field and one absent method, bought now instead of unpicked later.

- **Remember is out of scope.** The session over-extended into it and the user pulled it back: no visible threat yet, and card scheduling, review algorithm and notifications are all remember's problem later. `note-mutability`, `note-ownership` and the duplicate-copy consistency worry stay recorded but stop driving decisions here.
- **Card→note anchors are carried from the start**, as part of card generation rather than as review tooling.

**The concrete ask this session now serves:** seeing, in the TUI, that a card *came into existence* and *which note it belongs to*. That single requirement ties together the three loose ends — a per-note state visible while browsing, a per-note card count, and the anchor that makes the link legible inside the note's text.

**Residual consistency requirement:** envelope delivery is at-least-once, so distill's note-save must be idempotent on `note_id` — redelivery must not produce a second note record. With Notion de-scoped there is no cross-store write left, so this is the whole of the concern.

**Live tension — distill is a fan-out, not a pipeline.** Because cards derive from distill's own note record, card generation never depended on a Notion write succeeding — the two were independent branches off `note-save`, not a chain. With Notion de-scoped only the `flashcard-gen` branch exists today, so the two-track status collapses to one track for now, but the shape and its consequence for `outbox-shared`'s parked flashcard-gen-trigger question (note-save enqueues within its own UoW) still stand.

**Inherited ground (not re-opened unless a tension forces it):**
- `outbox-shared`: `distill` is realized as outbox-consuming processes filtering by envelope `type`; first event `note_approved` carries a denormalized snapshot (`note_id`, `session_id`, `topic{id,label}`, `content`, `tags[{id,label}]`, `approved_at`).
- `backend-stack`: a Notion write and a Postgres outbox row cannot commit atomically — "needs an explicit answer when the note-save worker is designed". The local-record-first shape above is that answer's basis: the local row commits transactionally with the outbox, and `notion_page_id` is filled in afterward, so a failed publish is a visible state rather than lost data.
- `overview-thougts`: rejected cards are soft-deleted and kept as a negative signal so the agent avoids regenerating near-duplicates — already a regeneration feature, which a run record needs to read.
- `tui-stack`: Ink + Zustand, Zustand scoped to background-task/notification state. Polling interval/backoff/cancellation deferred to implementation. `App` today renders `CaptureScreen` directly; there is no router.

- **An anchor is an abstraction, not a storage format.** The user wants a block/paragraph reference for the "jump to this block" gesture but has no markdown parser yet, so the anchor sits behind one operation — resolve an anchor against note content to a position — with the concrete form free to change underneath.
- **A markdown parser is coming regardless**, because LLM output is markdown and the TUI has to render it. Its cost is therefore not chargeable to anchoring.
- **Notification on cards landing is a one-time message**, fired when a note's cards are ready, not a persistent indicator.

- **The stored anchor is a verbatim quote; the block position is derived at read time** by the parser. Accepted on the condition that the parser can actually locate the quote — which makes match robustness a real design constraint, not a detail.
- **An anchor that does not resolve rejects the card.** The user's reasoning: the note is the source of truth for its cards. This turns the earlier principle — it is honest to build cards from grounded, endorsed knowledge — from a value statement into an enforced invariant, and it is the only generation invariant the design has.

- **A run that loses proposals to validation is still a success.** Rejected proposals are retained rather than dropped; an internal endpoint for inspecting them is wanted eventually, not now. Keeps the only free quality metric the project has — the discard rate.
- **`/notes` orders by update date** (of the note and its cards). Sorting is expected to be handed to remember later, since cards will have a scheduler of their own.

**Open question:** how quote matching is normalized so honest cards are not rejected on formatting alone — proposed: match against the parser's *rendered block text* rather than raw markdown, collapsing whitespace and inline emphasis, and require an anchor to resolve inside a single block.

**Current thread — who wraps a generated card.** The user asked whether cards should already be "wrapped" in the remember domain at generation time. Proposed answer, mirroring the note decision the user already accepted: distill owns the card's **content** (question, answer, `note_id`, anchor), remember owns the **learning state** about it, keyed by `card_id`. The two have genuinely different lifecycles — content is written once, state changes on every review — and remember wraps a card **lazily**, on first encounter, so a card with no remember-side item simply *is* a new card. That makes the deferral free: no envelope to emit now, no backfill later. The one place remember writes back into distill is card rejection, since `overview-thougts` keeps rejected cards as a negative signal for *generation* — so rejection is a command to distill, the same shape as remember asking distill to amend a note.

**Current thread — the scheduling adapter.** The user proposes wrapping `py-fsrs` behind an adapter for resilience to an algorithm change. Two separations raised in response: FSRS *schedules reviews*, it does not *generate cards*, so that port belongs to remember and is not needed yet; and the port distill actually needs now is **card generation** (LLM-backed, in-memory first), for which capture already has the pattern in its `reply_generation` / `topic_extraction` / `confidence_assessment` in-memory adapters. The one distill-side consequence of FSRS existing later: a freshly generated card should be born with **no scheduling state at all**, since "never scheduled" is exactly FSRS's notion of a new card, and initializing it in distill would leak remember's algorithm upstream.

**Distilled into an ADR on 2026-09-02:** `context/adrs/distill-domain-shape/` — three aggregates (Note, Card, DiscardedProposal), the grounding invariant, the quote-anchor with block position derived at read time, the two-consumer outbox chain, ownership boundaries against remember, and the Notion deferral as `backend-stack`'s owed atomicity answer. The ADR builds on `backend-stack` rather than superseding it, and deliberately excludes the TUI shell as `tui-stack` territory. This session stays open; anything reopened here would need its own ADR or an amendment while that one is still `open`.

**Deferred, recorded but no longer driving:** whether capture's `Note` and distill's note should stop sharing a name; whether a capture session opened from a review links back to the card that prompted it; note mutability and versioning beyond the agreed insurance.

**Raised, out of scope here:** sessions should also be listable and resumable (`/sessions`) — a capture-side concern, but it means the dispatcher routes into capture too, not only distill.

## Log

### 2026-09-02 — distill-scope: Distill = persist approved note to Notion + generate cards from it — OPEN
Why: the user's opening seed for the pillar. Matches `outbox-shared`'s already-accepted two-process split (note-save, flashcard-gen) and the `backend-stack` ADR's "notes go to Notion" decision, so the scope statement is consistent with prior ground. Left OPEN because the seed does not yet say what distill *owns* as its own model versus what it merely forwards to Notion.

### 2026-09-02 — card-source: note vs. session as the flashcard generation input — OPEN
Why: the user explicitly flagged themselves as conflicted. Raised here that the choice is not purely about generation quality: the note-only path is fully served by the existing `note_approved` snapshot, whereas pulling in the session transcript forces either a much heavier envelope or a cross-module read into capture — which is the exact coupling `outbox-shared` designed the snapshot payload to prevent. A third framing was offered: note as the source of record, transcript as optional grounding context, which still pays the same transport cost.

### 2026-09-02 — note-identity-split: Notion owns the body, Postgres owns identity and metadata — OPEN
Why: raised as a tension against the user's "distill saves the note to Notion" framing. The queries the user wants (`/notes` listing, note↔card binding, distill status polling) are all things Notion is a poor and slow store for. Rather than reversing the `backend-stack` ADR, proposed splitting: the Notion page holds the note body, a local row holds `note_id`, `notion_page_id`, status, topic/tags and the card edges. Not yet put to the user as a decision.

### 2026-09-02 — status-polling: what the pollable status is attached to — OPEN
Why: the user wants phase-one polling on "note ready" / "cards ready" but did not say what resource carries that status. Three candidates surfaced — a field on distill's note record, the outbox envelope (already reachable via the existing `GET /_outbox` endpoint), or a dedicated job resource. Noted that polling the envelope would expose transport mechanics to a client the `repo-shape`/`tui-stack` decisions want kept thin.

### 2026-09-02 — flashcard-gen-trigger: park re-opened now that distill is being designed — OPEN
Why: `outbox-shared` parked "whether note-save produces a second envelope for flashcard-gen" solely because distill did not exist yet as real consumer code. This session is that design, so the park's stated precondition is gone. Three shapes named: note-save enqueues a `note_saved` envelope in its own UoW (per-step retry, distill becomes its own producer), capture enqueues both up front (creates an ordering problem — flashcard-gen has nothing to read yet), or one handler does both (simplest, but a retry re-runs the Notion write and demands idempotency).

### 2026-09-02 — tui-dispatcher: slash-command dispatcher as the TUI's interaction shell — OPEN
Why: the user is warming to a Claude-Code-style `/` command set but says the command set itself is not settled. Suggested deferring the command *set* and settling the dispatcher *shape* instead (how input is split between command and message, where the command registry lives, how a command declares arguments, what a command renders). Also raised that `/cards <note-id>` implies pasting a UUID, and that selecting a note from `/notes` and drilling in may be the better binding gesture — which changes the design from id-addressed to selection-addressed.

### 2026-09-02 — note-identity-split: accepted, with local content carried from the snapshot — ACCEPTED
Why: user agreed to the split and added a requirement — reading a single note's content inside Weles matters for the learning loop (holding a card, wanting to confirm something against the note). Reading that from Notion is cheap in API terms but lossy in fidelity: markdown → Notion blocks → back to markdown is a round-trip that has to be re-implemented and never round-trips cleanly. Resolved by noticing the `note_approved` envelope already carries `content` — keeping it on the local record makes the read path local and instant, costs nothing new, and needs no document store. Notion stays a write target, so `backend-stack` is untouched.
Supersedes: 2026-09-02 note-identity-split (OPEN).

### 2026-09-02 — card-source: note only; a richer envelope version is the escape hatch if quality disappoints — ACCEPTED
Why: user resolved their own conflict on a product principle rather than a technical one — it is honest to build cards from knowledge already grounded and endorsed, so what was deliberately cut from the note draft should not come back as a card. Same line as `overview-thougts`' `approval-policy`. If card quality turns out poor, the agreed remedy is minting a new envelope version with a fuller payload, which keeps the fix inside the outbox contract instead of letting distill read capture's stores.
Supersedes: 2026-09-02 card-source (OPEN).

### 2026-09-02 — card-anchor: each card carries a pointer into the note fragment it came from — OPEN
Why: raised as a consequence of `card-source`. If a card may contain nothing outside its note, every card can cite the fragment it derives from. That upgrades the user's own read-the-note use case from "jump to the note" to "jump to the place in the note", and gives a checkable quality property — a card with no coverage in the note text is a fabricated card. Not yet responded to.

### 2026-09-02 — notion-drift: local content as a provenance record rather than a mirror — OPEN
Why: user expects to edit notes in Notion by hand ("gorzej jak mnie pokusi"), which desynchronizes the local copy. Three shapes named — accept drift, read-through to Notion on open, or full sync with a conflict policy. Proposed reframe: the local content is not a stale mirror but an immutable record of *what the cards were made from*, which makes drift correct by construction and keeps `card-anchor` pointers valid permanently. Noted that this ties drift to regeneration: a Notion edit is precisely what makes a regeneration meaningful rather than an LLM re-roll on identical input, implying a versioned snapshot per run.

### 2026-09-02 — status-polling: process status wants a per-run record, because regeneration is expected — OPEN
Why: user confirmed `_outbox` is an ops endpoint and that the distill *process* should carry the status, and separately confirmed regeneration of cards is wanted — later, but expected. That combination decides the earlier open shape: with more than one run possible per note, status stops being a property of the note and becomes a property of a run. Cost of modelling it now is near zero given the `InMemoryFirst` convention means there is no schema to migrate yet. A run record also has somewhere to read `overview-thougts`' soft-deleted rejected cards from, which regeneration needs to avoid near-duplicates.
Supersedes: 2026-09-02 status-polling (OPEN) — the "envelope vs. note vs. job resource" question narrows to "field on the note vs. run record", leaning run record.

### 2026-09-02 — regeneration: card regeneration is expected, not in the first cut — ACCEPTED
Why: user stated it directly. Recorded as a shaping constraint rather than scope: nothing in the first cut should make regeneration painful to add, which is what pushes `status-polling` toward a run record and `notion-drift` toward versioned snapshots.

### 2026-09-02 — tui-shell: commands open as an overlay over the capture view — ACCEPTED
Why: user picked overlay over screen swap, unprompted by the trade-off. Settles the second half of the same question for free — an in-flight capture session survives a command by construction, because the overlay never unmounts `CaptureScreen`. `App` still has to grow from rendering `CaptureScreen` directly into hosting a dispatcher plus an overlay layer.

### 2026-09-02 — distill-steps: fan-out (notion-publish ∥ flashcard-gen) rather than a pipeline — OPEN
Why: follows from `note-identity-split`. Because cards derive from the *local* snapshot, card generation has no dependency on the Notion write succeeding, so the two are independent branches off note-save rather than a chain. Answers `outbox-shared`'s parked flashcard-gen-trigger in favour of note-save enqueuing envelopes within its own UoW, and makes a failed Notion publish non-blocking for the learning loop. Consequence not yet accepted: the process status becomes two-track rather than a single linear ladder.

### 2026-09-02 — notion-descope: Notion drops out of this design for now — ACCEPTED
Why: the prototype is entirely in-memory per the `InMemoryFirst` layering rule, so a publish branch has nothing to prove and nothing to run against. Cheap because the `note-identity-split` decision already made Notion a pure write target — removing it deletes a branch rather than reshaping the domain. `backend-stack`'s "notes go to Notion" is not reversed, only deferred: publishing returns as one more output adapter behind the same port.
Consequence: with only `flashcard-gen` left, distill's fan-out has a single branch today and the two-track status collapses to one track. The remaining justification for distill holding its own note record is module isolation alone, not query performance — worth being honest about, since it is now one reason instead of two.

### 2026-09-02 — notion-drift: retires with Notion, but the underlying question survives — PARKED
Why: the drift thread was entirely about hand-edits made in Notion, which cannot happen while Notion is de-scoped. Parked rather than rejected — it returns verbatim if Notion publishing returns. The versioned-snapshot mechanism it proposed is *not* parked with it: the user immediately re-raised the same mutability problem from an internal source, so the mechanism outlived its original trigger.
Supersedes: 2026-09-02 notion-drift (OPEN).

### 2026-09-02 — note-mutability: remember may correct or extend a note, so a note may not be frozen — OPEN
Why: user flagged this as the likely foot-gun in the whole direction — once `remember` exists, working through cards is exactly when a note turns out to be wrong or incomplete, and the natural gesture is to fix it. That makes Weles itself the editor, which is a harder case than an external Notion edit because it is a first-class designed behaviour rather than something we may choose to ignore. Proposed shape: append-only note versions, with a distillation run pointing at the version it consumed, so card anchors stay valid while the note still grows — and an amendment becomes the natural, *meaningful* trigger for regeneration that the Notion pull-back was previously supposed to provide.

### 2026-09-02 — note-ownership: who owns a note if remember can change it — OPEN
Why: raised as the structural half of `note-mutability`. Three shapes named: distill stays owner and remember sends it an amend command (keeps three modules and the outbox as the seam); the note moves into `domain/shared` (rejected in the framing — notes are a product artifact, not a cross-cutting abstraction); or a fourth module owns the knowledge artifacts with distill and remember both as clients (honest, since the three pillars are *processes* while notes and cards are *artifacts*, but a large restructure to take on speculatively). Recommended the first.

### 2026-09-02 — remember-as-note-producer: remember may author new notes, not only amend them — OPEN
Why: the user's phrase covered two different things — corrections to an existing note, and writing a new one off the back of a review session. The second is structurally bigger: it means the capture → distill edge is not the only way a note is born, so `note_approved` would not be distill's only input and the envelope type should not be assumed capture-specific. Surfaced now because it is cheap to keep the door open and expensive to discover later.

### 2026-09-02 — note-ownership: distill owns the note, remember asks it for changes — ACCEPTED
Why: user judged this consistent with the handoff capture already makes to distill, and explicitly did not want the note living anywhere else for now. The "artifacts deserve a home outside the process pillars" alternative is set aside as a speculative restructure, not refuted — it can return if remember turns out to push hard against distill's ownership.
Supersedes: 2026-09-02 note-ownership (OPEN).

### 2026-09-02 — remember-as-note-producer: remember does not author notes; it opens capture mode — REJECTED
Why: user reframed it better than the question did — remember does not need to be a note producer, it just needs to be able to open capture, because it is all one application and the modes weave into each other. That preserves a single birth path for notes, so `note_approved` stays distill's only input and the envelope type needs no genericising. Rejects the complication rather than the underlying need.
Supersedes: 2026-09-02 remember-as-note-producer (OPEN).
Consequence: opens a smaller question — whether a capture session started from a review carries a provenance link back to the card that prompted it, which is what would make the user's "branching" idea visible later.

### 2026-09-02 — note-versioning-insurance: no immutability invariant, version pinned at 1 — ACCEPTED
Why: user accepted the minimal shape. The prototype builds neither amendment nor regeneration, but avoids giving distill's note record a "content never changes after save" invariant, and has a distillation run reference a note version even while that version is always 1. Cheap now, expensive to unpick after `note-mutability` lands.

### 2026-09-02 — consistency-surface: two `Note` types are one lifecycle apart, not two copies of one thing — OPEN
Why: user's addition to the foot-gun — writes spread over multiple stores invite eventual-consistency problems. Noted that de-scoping Notion already removed the only cross-store write, so the residual surface is narrower than feared: capture's `Note` and distill's note record are two rows in one store, and the real hazard appears only once distill's copy becomes mutable, at which point capture's copy would silently be wrong. Proposed reading: capture's `Note` is the approved *output of a session* — already frozen post-approval in code, since every mutator routes through `_ensure_draft` — while distill's note is the living knowledge artifact. Under that reading they never diverge because they are not the same thing, and the only real requirement left is that distill's note-save be idempotent on `note_id`, since envelope delivery is at-least-once.
Consequence raised, not decided: two different lifecycles sharing the name `Note` across two modules is where the confusion will actually land.

### 2026-09-02 — scope-boundary: remember is out of scope; distill stops designing around it — ACCEPTED
Why: the session had been projecting forward into remember (amendment, versioning, note ownership under review-driven edits) and the user pulled it back — no threat is visible yet, and the review algorithm, scheduling and notifications belong to remember when it is designed. Agreed: card *generation* and card↔note *visibility* are distill's; learning from cards is not. The `note-mutability`, `note-ownership` and `consistency-surface` entries stay on the record but stop driving decisions in this session.
Consequence: the versioning insurance from `note-versioning-insurance` stands as the cheap hedge it was scoped to be, and nothing further is built against a future remember.

### 2026-09-02 — card-anchor: carried from the start, as part of generation — ACCEPTED
Why: user confirmed anchors go in now, scoped as part of flashcard generation rather than as review tooling. Serves the concrete ask they stated — being able to see visually that a card exists and which note it belongs to — and gives generation a cheap grounding check for free.
Supersedes: 2026-09-02 card-anchor (OPEN).
Proposed but not yet confirmed: an anchor is a **verbatim quote** from the note rather than character offsets or block indices — it is the form an LLM emits reliably, a quote that fails to occur in the note is a detectable fabrication, and offsets for highlighting can be derived from it at read time.

### 2026-09-02 — status-polling: run record withdrawn for now in favour of a current-status field — OPEN
Why: the run-record argument rested entirely on regeneration, which `scope-boundary` has just pushed out with the rest of remember. What the TUI actually needs to render a `/notes` row is the *current* state per note, not a history of attempts. Withdrawing the push rather than asking a third time; the hedge that keeps it cheap later is already in `note-versioning-insurance`.
Supersedes: 2026-09-02 status-polling (OPEN) — narrows back from "run record" to "current status on the note record", with runs arriving only alongside regeneration.

### 2026-09-02 — distill-visibility: the `/notes` row and the note view are distill's real deliverable — OPEN
Why: user named the concrete goal — seeing that a card came into existence and is bound to a given note. Two moments were distinguished: the background moment (cards land while you are elsewhere, which is exactly the cross-screen notification state `tui-stack` chose Zustand for) and the browsing moment (a `/notes` row carrying topic, distill state, and a card count; entering a note shows its content with anchored fragments marked, plus its cards). Not yet settled what each surface shows.

### 2026-09-02 — card-anchor: the anchor is an abstraction with one resolve operation; storage form deferred — ACCEPTED
Why: user prefers a block/paragraph reference because it gives a natural "jump to this block" gesture that opens the note in place, but has no markdown parser yet. Rather than choose the storage form now, the anchor sits behind a single operation — resolve an anchor against note content to a position — which a quote-matching resolver and a block-index resolver both satisfy. Cheap seam, and it keeps the UX target without paying for the parser first.
Supersedes: 2026-09-02 card-anchor (ACCEPTED) — anchors still ship with generation; only their concrete form is now deferred behind an abstraction.
Proposed, not confirmed: store the **quote** and derive the block position at read time. Argued as strictly dominant once a parser exists — same jump-to-block gesture, survives paragraph insertion where a stored index silently shifts, fails loudly on deletion, and doubles as a grounding check. A stored block index buys the gesture and nothing else.

### 2026-09-02 — markdown-parser: needed for rendering anyway, so not an anchoring cost — OPEN
Why: user observed that LLMs speak markdown, so a parser is coming regardless — and the TUI has to render headings, lists and code blocks in a terminal whatever anchors turn out to be. Noted so that the block-index anchor form is not wrongly charged the parser's cost when it is reconsidered.

### 2026-09-02 — distill-visibility: stable list order with a state badge, plus a one-time ready message — OPEN
Why: user accepted a `/notes` row carrying topic, state and card count, floated either colouring a card-less note or sorting generating notes to the top, and picked a one-time message fired when a note's cards are ready over a persistent indicator. Pushed back on the sorting option: order that changes when generation finishes makes a row jump under the cursor mid-browse, whereas a badge on a stable ordering stays legible and the one-time message already does the "look at me" job. Also raised that "no cards" has three distinct causes worth distinguishing rather than one colour — not generated yet, generated zero (a legitimate outcome given the product's own "not every note deserves memorizing"), and generation failed.

### 2026-09-02 — card-anchor: quote is stored, block position derived at read time — ACCEPTED
Why: user took the synthesis rather than the either/or, conditional on the parser being able to find the quote. That condition is the substance: matching has to survive an LLM normalizing whitespace or dropping inline emphasis, so the proposal is to match against the parser's rendered block text rather than the raw markdown source, and to require an anchor to resolve within a single block. Under that rule the parser does not merely enable the jump-to-block gesture — it also makes matching more forgiving than a raw string search would be.
Supersedes: 2026-09-02 card-anchor (ACCEPTED) — the deferred storage form is now decided; only the matching rule is open.

### 2026-09-02 — card-grounding: an unresolvable anchor rejects the card; the note is SoT for its cards — ACCEPTED
Why: user chose rejection over flagging, on the grounds that the note is the source of truth for the cards derived from it. Promotes the session's earliest principle — cards come from grounded, endorsed knowledge — from a stated value into the one enforced invariant generation has. Distinct from `overview-thougts`' soft-deleted *user*-rejected cards, which are a negative signal for a future generation; this is validation at write time.
Consequence, not yet decided: whether rejected proposals are dropped silently or kept for observability, and whether a run that loses most of its proposals is still a success. Noted that rejection must **not** trigger an automatic re-generation — the session already established that re-rolling an LLM on identical input is meaningless.

### 2026-09-02 — card-grounding: a partial run is a success; rejected proposals are retained — ACCEPTED
Why: user settled the consequence left open by the rejection invariant — six proposals with four rejected is a run that produced two cards, not a failed run. Rejected proposals are kept rather than discarded, with an internal inspection endpoint wanted eventually but explicitly not now. Retention is what preserves the discard rate, which is the only generation-quality metric this project gets for free.

### 2026-09-02 — distill-visibility: order by update date, sorting later ceded to remember — ACCEPTED
Why: user picked ordering by update date of the note and its cards, which is stable enough for browsing without the row-jumping problem that sorting by generation state would cause. Sorting is expected to move to remember eventually, since cards will carry scheduler-driven ordering of their own. The three-state "no cards" distinction (in flight / generated zero / failed) was not responded to and remains proposed.
Supersedes: 2026-09-02 distill-visibility (OPEN) — ordering decided; badge vocabulary still open.

### 2026-09-02 — scheduling-adapter: FSRS behind a port is right, but it is remember's port, not distill's — OPEN
Why: user proposed wrapping `py-fsrs` in an adapter to stay resilient to an algorithm change. Agreed in principle — it follows the project's own hexagonal and `InMemoryFirst` rules, and the domain must not import a third-party scheduler under the layering rule. Two separations raised: FSRS *schedules reviews* rather than *generating cards*, so the port belongs to remember and is not needed in this session's scope; and the insulation only works if the port hides FSRS's *state model* rather than merely renaming it — a port exposing stability/difficulty/retrievability would still break the domain on a swap to SM-2 or Leitner. Proposed shape: the card carries an **opaque** scheduler state the domain never interprets, plus a `due_at` it can query on.
Consequence in scope here: a freshly generated card is born with **no** scheduling state, since "never scheduled" is already FSRS's own notion of a new card and initializing it in distill would leak remember's algorithm upstream.

### 2026-09-02 — card-generation-port: the LLM generation port is the one distill needs now — OPEN
Why: raised as the counterpart to `scheduling-adapter`. Distill's own algorithmic seam is card generation, and capture has already established the pattern for exactly this kind of port with its in-memory `reply_generation`, `topic_extraction` and `confidence_assessment` adapters. Under `InMemoryFirst` a deterministic in-memory generator proves the whole distill loop — envelope, run, anchors, rejection invariant, TUI visibility — before any LLM is wired in.

### 2026-09-02 — card-ownership: distill owns card content, remember owns learning state, wrapped lazily — OPEN
Why: user asked whether generated cards should already be wrapped in the remember domain, explicitly as a forward-looking question that can be delivered later. Answered by reusing the split the user already accepted for notes: distill owns the content artifact (question, answer, `note_id`, anchor), remember owns the state about it keyed by `card_id`. Content is written once and learning state changes every review, so folding them into one entity means every review write touches the content. Wrapping is **lazy** — no remember-side item exists until a card is first encountered, which is the same "never scheduled = new card" logic as `scheduling-adapter`. That removes both the need to emit a `cards_generated` envelope now and the need to backfill one later, making the deferral genuinely free rather than merely postponed.
Consequence: the one write remember makes back into distill is card **rejection**, because `overview-thougts` keeps rejected cards as a negative signal for *generation* — a distill concern. So rejection is a command to distill, structurally identical to remember asking distill to amend a note under `note-ownership`.

### 2026-09-02 — session-queries: sessions should be listable and resumable too — OPEN
Why: user raised it while answering the dispatcher question. Capture-side rather than distill-side, so not settled here, but it establishes that the dispatcher is an app-wide shell routing into every pillar, not a distill-specific viewer.
