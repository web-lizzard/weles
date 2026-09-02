## Context

`context/adrs/capture-flow-domain-shape/` ends exactly where this decision begins: an approved `Note`, and an outbox envelope written by the `ApproveNote` handler inside the same `UnitOfWork`. `context/duck-sessions/outbox-shared/` settled what that envelope carries — a **denormalized snapshot** (`note_id`, `session_id`, `topic {id, label}`, `content`, `tags [{id, label}]`, `approved_at`), chosen specifically so a consumer never reaches back into capture's repositories to resolve labels. This decision builds on `context/adrs/hexagonal-arch-shape/` unchanged: three layers, CQRS-lite, an application-owned `UnitOfWork`, InMemoryFirst, no bus.

The material comes from the duck session `context/duck-sessions/distill-pillar/`.

Three inherited threads land here rather than anywhere else.

1. **`outbox-shared` parked the flashcard-generation trigger** — whether note-save enqueues a second envelope — explicitly because "distill doesn't exist yet as real consumer code". That precondition is gone.
2. **`backend-stack` left an owed answer**: a Notion write and its related Postgres bookkeeping "cannot commit atomically. This needs an explicit answer when the note-save worker is designed." This is that worker.
3. **`overview-thougts` made flashcards a deliberate exception to the app-wide approval policy** — the agent generates and saves them, the user reviews afterwards — and settled that user-rejected cards are kept as a negative signal rather than purged.

Four forces pull against each other.

**Module isolation versus duplication.** The snapshot payload exists to keep distill independent of capture's stores, which necessarily means the note's content lives in two rows. While Notion was in the picture those rows were in different stores and the duplication bought query performance as well as isolation. Deferring Notion removes that second justification, and the duplication has to stand on isolation alone.

**Designing for remember versus not.** The session repeatedly extended into the third pillar — note amendment during review, versioning, note ownership under review-driven edits — and the user pulled it back: no visible threat yet, and the review algorithm belongs to remember when remember is designed. What survives that pullback is only the cheap hedging that would be expensive to retrofit.

**The product's own filter.** `context/foundation/project-overview.md` states that a second brain remembering everything indiscriminately "is just a second junk drawer" and that the value is in deciding what is worth carrying forward. A note that yields zero cards is therefore a correct outcome, not a failure, and the model has to be able to say so.

**Honesty of derivation.** The user's stated principle for card generation — it is honest to build cards from knowledge already grounded and endorsed — started as a reason to prefer the note over the session transcript. It ends up as the only enforced invariant this domain has.

The TUI shell that surfaces all of this (the command dispatcher, overlay behaviour, list ordering, the one-time "cards ready" message) is deliberately **out of scope** here; it is `context/adrs/tui-stack/` territory and was left under-argued on purpose. This decision fixes only what the backend owes that shell.

## Decision

The distill module lives at `domain/distill/` and `application/distill/`, per `hexagonal-arch-shape`'s directory convention. Its scope is: consume an approved note from capture, hold it, and generate grounded cards from it. Review scheduling is not distill's; neither is the client shell.

### Notion is deferred, not reversed

The prototype builds no Notion publication branch. `backend-stack`'s decision that notes belong in the user's Notion workspace stands as the intended end state; it simply has nothing to prove while the entire system runs on in-memory adapters under `hexagonal-arch-shape`'s InMemoryFirst rule.

The deferral is cheap because the shape adopted below makes Notion a pure write target: distill's note record is complete without it, so publication is one more output adapter behind one more port, added later without reshaping the domain.

This also answers `backend-stack`'s owed atomicity question, in two halves. For now: with a single store there is no cross-store write left to make atomic. For later: publication is its **own** step, so the local record commits transactionally with the outbox and `notion_page_id` is filled afterwards — a failed publish is a visible state on a saved note, never a lost note.

### Three aggregates

**Note** (distill's) — `id`, `session_id`, `topic: TopicSnapshot`, `content`, `tags: list[TagSnapshot]`, `version`, `distillation_status`, `approved_at`, `created_at`.

- Its `id` **is** the capture note's id. The same note travels between modules under one identity; two ids for one artifact would make every cross-module conversation ambiguous for no gain in a single-user tool. Redelivery idempotency then falls out of the identity itself rather than needing a separate uniqueness rule.
- `topic` and `tags` are **embedded value objects carrying label and source id**, not references into capture's vocabulary aggregates. The snapshot is denormalized by design, and resolving a label by reaching into `domain/capture/` is exactly the coupling the envelope exists to prevent.
- `version` exists and is pinned at `1`. Nothing in this version amends a note.
- The aggregate carries **no immutability guard**. Capture's `Note` is frozen after approval — every mutator routes through `_ensure_draft` — because it is the terminal output of a session. Distill's note is the living knowledge artifact and is deliberately not given the mirror-image invariant, so that amendment can land later without unpicking a rule.
- `distillation_status` is `generating | ready | failed`. A note exists in distill only after it is saved, so there is no "unsaved" rung. `ready` with zero cards is a **success**.

**Card** — `id`, `note_id`, `note_version`, `question`, `answer`, `anchor: Anchor`, `status`, `created_at`.

- A `Card` that exists is grounded, by construction (see below).
- It carries **no scheduling state of any kind**. "Never scheduled" is already what a new card means to any spaced-repetition algorithm, so initializing anything here would only pull remember's algorithm upstream.
- `status` is `active | rejected`. `rejected` is the negative signal `overview-thougts` settled on, and **nothing in this version sets it** — the same forward-looking extension point, and the same accepted cost, as `NoteStatus.discarded` in `capture-flow-domain-shape`.

**DiscardedProposal** — `id`, `note_id`, `question`, `answer`, `quote`, `reason`, `created_at`. A generation proposal that failed grounding, retained rather than dropped. It is deliberately **not** a `Card` with a status: a card whose anchor does not resolve would violate the one invariant the `Card` aggregate exists to guarantee.

### The grounding invariant

Every card carries an anchor into the note it came from. **An anchor that does not resolve rejects the card.** The note is the source of truth for its cards.

An `Anchor` stores a **verbatim quote**. The block position for a "jump to this block" gesture is derived at read time by the parser, not stored. Storing the quote and deriving the position dominates storing the position: it yields the same gesture, survives an inserted paragraph where a stored index silently shifts to the wrong block, fails loudly rather than quietly on a deleted one, and doubles as the fabrication check that makes the invariant enforceable at all.

Matching runs against the parser's **rendered block text** — whitespace collapsed, inline emphasis stripped — rather than the raw markdown source, because a model quotes what it reads, not the source it was given. An anchor must resolve **within a single block**; a quote spanning a paragraph boundary has no block to jump to and is rejected.

Resolution needs the parser, which is an adapter, so the `Card` aggregate cannot self-validate. An application service resolves each proposal's quote through the parser port and constructs a `Card` only from what resolved — the same shape `capture-flow-domain-shape` used for vocabulary reconciliation, where "the aggregates never see candidate strings or similarity scores, only already-resolved objects".

A run that loses proposals to grounding is a **success with fewer cards**, not a failure. Rejection never triggers automatic regeneration: re-rolling a model on identical input is not a retry, and the session ruled it out.

### Two consumers, chained through the outbox

Distill runs as two handlers filtering by envelope type, closing `outbox-shared`'s parked question:

- `note_approved` → **note-save**: persists distill's `Note` and, in its **own** `UnitOfWork`, enqueues `note_saved`.
- `note_saved` → **flashcard-gen**: generates proposals, resolves anchors, persists cards and discarded proposals, moves `distillation_status`.

Distill therefore has its own `UnitOfWork` with an `outbox` member, exactly as capture does under `outbox-shared`.

The two steps stay separate even though only one branch exists today. Notion publication will be the second branch off `note_saved`, and the split already pays for itself: a failed model call must not re-run the save, and a fast local write must not be coupled to a slow, expensive one.

Envelope delivery is at-least-once, so both handlers are idempotent — note-save on the note's id, flashcard-gen on `(note_id, note_version)`.

### Ownership boundaries

**Distill owns the note.** Remember, when it exists, does not hold its own copy; it asks distill to change one.

**Distill owns a card's content; remember will own the learning state about it**, keyed by `card_id`. The two have genuinely different lifecycles — content is written once, learning state changes on every review — and folding them into one entity would make every review write touch the content.

Remember wraps a card **lazily**, on first encounter: a card with no remember-side record simply *is* a new card. Distill therefore emits no `cards_generated` envelope and leaves no backfill behind, which is what makes the deferral free rather than merely postponed.

**Notes are born only in capture.** Remember does not author notes; it opens capture mode and the ordinary approve → `note_approved` path runs. `note_approved` stays distill's only input.

The one write remember will make back into distill is card **rejection**, because the consumer of that negative signal is generation — a distill concern. It is a command into distill, structurally identical to remember asking distill to amend a note.

### Ports

Beyond a repository port per aggregate:

- **`CardGeneration`** (outbound) — note content in, card proposals out, each a question, an answer, and a quote. This is distill's algorithmic seam, and under InMemoryFirst a deterministic in-memory generator proves the whole loop — envelope chain, grounding, status, queries — before a model is wired in. Capture has already established the pattern with its in-memory `reply_generation`, `topic_extraction` and `confidence_assessment` adapters.
- **`NoteDocumentParser`** (outbound) — markdown to blocks with rendered text. Needed for terminal rendering regardless of anchoring, so anchoring is not charged its cost.

No scheduling port is defined here. When one is, it must hide the algorithm's **state model**, not merely rename it: a port exposing FSRS's stability/difficulty/retrievability would still break the domain on a swap to SM-2 or a Leitner box. The shape that survives a swap is an opaque scheduler state the domain never interprets, plus a `due_at` it can query on.

### Queries

Per CQRS-lite, query handlers read straight into DTOs against the same store, with no projection:

- **list notes** — id, topic label, tag labels, `distillation_status`, card count, last-updated. Ordered by update date across the note and its cards. The three "no cards" cases are distinguishable from this row alone: `generating` (in flight), `ready` with zero cards (a correct outcome), and `failed`.
- **get note** — content plus its cards' anchors resolved to block positions.
- **list cards for a note**.

The note-to-card binding is addressed by **selection**, not by id: a card id or note id is an alternative entry point, never the expected gesture.

### Naming

Capture's `Note` and distill's note keep the same class name, disambiguated by module path. Renaming a shipped, tested aggregate buys readability at the cost of churn, and the codebase already namespaces by bounded context.

## Consequences

- A note's content exists in two rows in one store. With Notion deferred, module isolation is the sole justification — the query-performance argument that used to reinforce it is gone. Capture's row is the historical record of what a session produced; distill's is the artifact. They are not maintained against each other, and nothing detects a divergence if one is ever introduced.
- Reusing capture's note id as distill's couples identity across modules. A future split of the two into separate databases cannot renumber, and any change to how capture mints note ids propagates into distill silently.
- `Card.status` carries a value nothing can set, exactly as `NoteStatus.discarded` does. Every exhaustiveness check over card status has a branch that cannot be exercised, and a reader has to be told that `rejected` is aspirational.
- The grounding invariant deletes work silently. A model that paraphrases instead of quoting loses good cards, and the only signal is the discard rate. `DiscardedProposal` preserves that signal, but nothing watches it — there is no threshold, no alert, and the internal endpoint for inspecting discards is wanted but not built.
- Only the quote is stored, so anchor resolution depends on the parser's behaviour forever. A parser upgrade that changes how a block's rendered text is produced can retroactively break resolution for cards written months earlier, with no stored fallback position to fall back on.
- No run record exists, so there is no history of generation attempts — no record of when a note was distilled, how many proposals it produced, or how the discard rate moved. Regeneration will need one and will start with an empty history for every note that predates it.
- Two envelope types and two handlers serve a single branch today. That is more machinery than one handler doing both writes, bought against a future branch and against retry granularity.
- `Note.version` is pinned at `1` and read by nothing but `Card.note_version`. It is dead data until amendment exists, and a reader will reasonably ask why it is there.
- `backend-stack`'s Notion decision now has no implementation path in the prototype, which costs the thing that motivated it: the user cannot browse their notes outside Weles. That is a real loss for as long as the deferral lasts, taken because an in-memory prototype cannot exercise a Notion adapter anyway.
- Two classes named `Note` with different lifecycles sit in one codebase. The cost lands on whoever imports the wrong one, and only the module path prevents it.
- Distill's status ladder has no "publishing" rung. Adding Notion later means adding both a rung and a second, independent track to a status that is currently linear, and the query DTO that the TUI reads will change shape at that point.

## Alternatives Considered

1. **Notion as the note store, read back through its API.** The literal reading of `backend-stack`. Rejected: the round trip is markdown → Notion blocks → markdown, which is lossy and has to be reimplemented, and the note's content already arrives free inside the `note_approved` envelope. API rate limits were never the problem; fidelity was.
2. **Notion as system of record with a local metadata-only row** (`note_id`, `notion_page_id`, status, card edges) and no local content. The intermediate that keeps `backend-stack` literally intact. Rejected for the prototype: keeping the content costs nothing, since it is already in the payload, and dropping it would put a lossy network round trip on the most common read path in the product.
3. **A separate document store for note bodies.** Raised by the user as a fallback if reading from Notion proved expensive. Rejected as unnecessary once the envelope's own `content` was noticed — a new store would be built to hold data already in hand.
4. **Cards generated from the session transcript**, or from the note with the transcript as grounding context. Genuinely tempting: more context than a distilled note carries. Rejected on two counts. Architecturally, it forces either a much fatter envelope or a cross-module read into capture, which is precisely the coupling the snapshot payload was designed to prevent. On the product side, the note is what the user endorsed, and material deliberately cut from the draft should not return as a card. The agreed escape hatch, if quality disappoints, is minting a **new envelope version** with a richer payload — keeping the fix inside the outbox contract.
5. **Anchor as character offsets into the note.** Precise and cheap to resolve. Rejected: models fabricate offsets far more readily than they misquote text, and an offset carries no way to detect that it is wrong.
6. **Anchor as a stored block or paragraph index.** The user's initial preference, and the most direct route to a "jump to this block" button. Rejected after argument: a stored index shifts silently to the wrong block when a paragraph is inserted above it, and it buys only the gesture — whereas a stored quote resolved through the parser buys the same gesture, degrades loudly, and validates grounding. The user accepted the swap on the condition that the parser can locate the quote, which is why the matching rule is part of this decision rather than an implementation detail.
7. **An unresolvable anchor flags the card as uncertain rather than rejecting it.** Keeps every generated card and defers judgement to the user. Rejected by the user on the grounds that the note is the source of truth for its cards — which promotes the session's opening principle from a stated value into the only enforced invariant the domain has.
8. **Storing failed proposals as `Card` rows with a distinct status.** Fewer tables. Rejected: a card whose anchor does not resolve contradicts the invariant the `Card` aggregate exists to guarantee, and every query over cards would then have to remember to exclude them.
9. **A `DistillationRun` aggregate carrying status, attempts and outcomes.** Argued for at length while card regeneration was still in scope, since status is a property of a run once there can be more than one. Withdrawn once the user pushed remember — and with it regeneration — out of scope: what the client actually renders is the *current* state of a note, and a run history serves a feature nobody is building. The hedge that keeps it cheap later is `Note.version`.
10. **Cards born into remember's domain, or wrapped by distill at generation time.** The user's own question. Rejected in favour of lazy wrapping: a card with no remember-side record already means "new", so eager wrapping would require distill to emit an envelope with no consumer today, or remember to backfill every pre-existing card tomorrow. Lazy wrapping needs neither.
11. **A card carrying its own scheduling state** (due date, stability, difficulty). Rejected: it pulls remember's algorithm upstream into distill, and makes every review write touch the row holding the card's content.
12. **Wrapping `py-fsrs` behind a port as part of this decision.** The user proposed it, and the wrapping itself is right — `layering` forbids the domain importing it, and `contract-testing` gives a deterministic port an obvious contract suite. Rejected here only on scope: FSRS schedules reviews rather than generating cards, so the port belongs to remember. What this decision takes from it is the one upstream consequence — a card is born with no scheduling state — plus the recorded warning that the port must hide the algorithm's state model to be worth anything.
13. **One handler performing both the save and the generation.** Simplest, and defensible while only one branch exists. Rejected: a redelivery after a failed model call would re-run the save, and a slow, expensive generation step would be coupled to a fast local write for no reason other than that the second branch has not arrived yet.
14. **A distinct id for distill's note plus a `source_note_id` reference.** The orthodox reading, keeping each module's identity its own. Rejected: it makes every cross-module conversation about "note X" ambiguous, and forces an explicit uniqueness rule to recover the redelivery idempotency that a shared id provides for free.
15. **Remember as a producer of notes**, authoring new notes off the back of a review session. Raised by the user and then reframed by them: remember does not need to author notes, it needs to be able to open capture. Rejected in that better form, which preserves a single birth path for notes and keeps `note_approved` as distill's only input.
16. **Renaming capture's `Note`** (to `SessionNote` or similar) to remove the collision with distill's. Rejected: it churns a shipped, tested aggregate and its whole test suite for a readability gain that module paths already mostly deliver. Recorded in `## Consequences` as an accepted hazard rather than resolved.
