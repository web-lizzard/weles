## Context

Distill is the middle pillar of `capture → distill → remember`. Its input contract is already fixed by `context/adrs/capture-flow-domain-shape/` and `context/duck-sessions/outbox-shared/`: `ApproveNote` writes a `note_approved` envelope inside the same `UnitOfWork` that approves the note, and that envelope carries a **denormalized snapshot** (`note_id`, `session_id`, `topic {id, label}`, `content`, `tags [{id, label}]`, `approved_at`) specifically so a consumer never reaches back into capture's repositories to resolve a label. `context/adrs/hexagonal-arch-shape/` supplies the layering, CQRS-lite, the application-owned `UnitOfWork`, InMemoryFirst and the no-bus rule, all unchanged here.

The material comes from the duck session `context/duck-sessions/distill-pillar/` and from `research.md` in this container.

**This decision replaces an earlier over-reaching one.** A first pass at this container distilled the duck session into a record that decided far more than the shape of a domain: an adapter-level quote-matching rule (rendered block text, collapsed whitespace, stripped emphasis, single-block resolution), read-model DTOs and their ordering while declaring the TUI out of scope in the same breath, and two fields it admitted in its own consequences were dead — a `version` pinned at `1` and a card status value nothing could set. That text is retained beside this file as `frame.md`: good input, not a decision. What follows keeps only what a domain and its ports must settle before code exists.

Four forces shape what is left.

**Isolation is the only thing paying for the duplicated note.** The snapshot exists so distill never reads capture's stores, which necessarily puts the note's content in two rows. Notion is deferred (see below), so the query-performance argument that used to reinforce the duplication is gone and isolation carries it alone.

**Remember is not being designed here.** The duck session repeatedly extended into the third pillar — note amendment, versioning, ownership under review-driven edits — and the user pulled it back each time. The user's explicit ask for this decision is a boundary that *holds*, so the boundary is stated as negative rules in the shape `hexagonal-arch-shape` states its layering rules, not as prose about ownership.

**The product's own filter.** `context/foundation/project-overview.md` holds that a second brain remembering everything indiscriminately "is just a second junk drawer". A note that yields zero cards is a correct outcome, and the model must be able to say so rather than reporting it as a failure.

**Honesty of derivation.** Cards are built only from knowledge the user already endorsed. In the duck session this began as a reason to prefer the note over the session transcript and ended as the only enforced invariant this domain has.

Notion is **deferred, not reversed**. `backend-stack`'s decision that notes belong in the user's Notion workspace stands as the intended end state; it has nothing to prove while the system runs on in-memory adapters under InMemoryFirst, and the shape below makes it a pure write target added later behind one more port. That also answers `backend-stack`'s owed cross-store atomicity question in two halves: with a single store there is no cross-store write left to make atomic, and when publication returns it is its own step, so the local record commits transactionally with the outbox and a failed publish is a visible state rather than a lost note.

## Decision

Distill lives at `domain/distill/` and `application/distill/` per `hexagonal-arch-shape`'s directory convention. Its scope is: consume an approved note, hold it, and generate grounded cards from it. Nothing else.

### Two aggregates

**Note** — `id`, `session_id`, `topic: TopicSnapshot`, `content`, `tags: list[TagSnapshot]`, `distillation_status`, `approved_at`, `created_at`.

- Its `id` **is** the capture note's id. One artifact travels between modules under one identity; two ids would make every cross-module conversation ambiguous for no gain in a single-user tool, and redelivery idempotency then falls out of identity rather than needing a separate uniqueness rule.
- `topic` and `tags` are **embedded value objects carrying label and source id**, never references into capture's vocabulary aggregates. Resolving a label by reaching into `domain/capture/` is exactly the coupling the snapshot payload exists to prevent.
- The aggregate carries **no immutability guard**. Capture's `Note` is frozen after approval — every mutator routes through `_ensure_draft` — because it is the terminal output of a session. Distill's note is the living knowledge artifact and is deliberately not given the mirror-image invariant, so amendment can land later without unpicking a rule.
- `distillation_status` is `generating | ready | failed`. A note exists in distill only once saved, so there is no "unsaved" rung. **`ready` with zero cards is a success.**

**Card** — `id`, `note_id`, `front: CardSide`, `back: CardSide`, `anchor: Anchor`, `discard: Discard | None`, `created_at`.

- `front`/`back` rather than `question`/`answer`: a flashcard is not always a question — term to definition, prompt to completion, cloze deletion are all the same two-sided artifact, and the domain should not presume the rhetorical form the generator happened to pick.
- **One value object, `CardSide`, used for both sides.** `domain/capture/value_objects.py` wraps every meaningful string this way — frozen, `value: str`, strip on the way in, its own `CoreException` on violation — and `Note.content` is a `NoteContent`, not a `str`, so bare strings here would be the exception rather than the rule. The four existing wrappers are separate classes because each carries its own length constant and its own error; a front and a back share both, so they share a type. Distinct `CardFront`/`CardBack` types would buy only swap-safety, which keyword construction already provides.
- **`CardSide` enforces: stripped, non-empty, and under a length bound.** The bound is deliberately generous and is a **sanity limit, not a quality gate** — unlike capture's, whose producer is a person being told they wrote too much, this side's producer is a model, so a construction failure means the proposal never becomes a card and leaves no discarded row. A card that is merely too long to be useful is a bad card, and the mechanism for a bad card is a `user_audit` discard, not a rejection at construction. Nobody should tighten this constant to raise card quality.
- **`Card` enforces one invariant of its own: the two sides must differ**, compared as plain inequality after canonicalization. Anything cleverer is a similarity judgement, which belongs to the generator, not the aggregate. Grounding, by contrast, `Card` cannot enforce at all, because it needs the parser.
- The new errors (`EmptyCardSideError`, `CardSideTooLongError`, `IdenticalCardSidesError`) are `CoreException` subclasses per `hexagonal-arch-shape`'s exception amendment, so each derives a `code` and owes an entry in the HTTP adapter's mapping table, which that ADR's subclass-walking test already checks.
- `Anchor` is a value object holding a **verbatim quote** from the note. How a quote is matched against note content is an adapter concern and is deliberately not decided here.
- `discard` carries the card's whole removal state and there is no status field beside it — see below.
- The card carries **no scheduling state of any kind** — see the boundary rules.

### The grounding invariant

Every card carries an anchor into the note it came from. **A card is live only while it carries no discard; a proposal whose anchor does not resolve within the note's content is persisted as a card discarded for `ungrounded`.** The note is the source of truth for its cards.

Resolution needs the parser, which is an adapter, so the `Card` aggregate cannot self-validate. An application service resolves each proposal's quote through the parser port and constructs cards from the outcome — the same shape `capture-flow-domain-shape` used for vocabulary reconciliation, where the aggregates never see candidate strings or similarity scores, only already-resolved objects.

A run that loses proposals to grounding is a **success with fewer cards**, not a failure, and rejection never triggers automatic regeneration: re-rolling a model on identical input is not a retry.

### One discard mechanism

A card is removed one way, whoever removes it. `Discard` is a value object — `reason: DiscardReason`, `detail: str | None`, `discarded_at` — and `Card.discard` either holds one or holds nothing. **Its presence is the discarded state.** There is no status field beside it, because two representations of one fact can disagree, and a card recorded as removed with no reason is a state the model should not be able to express.

`DiscardReason` has two values and both are settable today:

- **`ungrounded`** — the system removed it: the anchor did not resolve, so the note does not support the card.
- **`user_audit`** — the person removed it while reviewing their own cards, through a `DiscardCard` command handler in `application/distill/commands/`.

The distinction is load-bearing rather than decorative, because the two feed opposite corrections. A rising `ungrounded` rate says the generator is fabricating and the prompt or the port is wrong. A rising `user_audit` rate says the generator is grounded but producing cards the person does not want, and `overview-thougts` keeps exactly that signal so a later generation avoids near-duplicates of what was already turned down. An undifferentiated "removed" would destroy the only thing the record is for.

A discard is **terminal**: nothing in this version restores a card.

### Two consumers, chained through the outbox

- `note_approved` → **note-save**: persists distill's `Note` in `generating` and, in the same `UnitOfWork`, enqueues `note_saved`.
- `note_saved` → **flashcard-gen**: generates proposals, resolves anchors, persists cards, moves `distillation_status` to `ready` or `failed`.

This closes the flashcard-gen-trigger question `outbox-shared` parked, whose stated precondition — that distill did not yet exist as real consumer code — is gone.

The split is bought by **retry granularity, not by a future branch**: the model call is slow, expensive and failure-prone while the note write is fast and local, and a redelivery after a failed generation must not re-run the save. That argument holds today, at one branch.

Delivery is at-least-once, so both handlers are idempotent on `note_id`: note-save no-ops when the note already exists (and therefore does not enqueue a second `note_saved`), flashcard-gen no-ops when `distillation_status` has already left `generating`.

### Ports

- **`NoteRepository`, `CardRepository`** (domain) — repository ports in the domain's own vocabulary.
- **`CardGeneration`** (application, outbound) — note content in, proposals out, each a question, an answer and a quote. This is distill's algorithmic seam; under InMemoryFirst a deterministic in-memory generator proves the whole loop — envelope chain, grounding, status — before a model is wired in, exactly as capture's in-memory `reply_generation`, `topic_extraction` and `confidence_assessment` adapters do.
- **`NoteDocumentParser`** (application, outbound) — markdown to blocks, and quote resolution against them. Needed for terminal rendering regardless of anchoring, so anchoring is not charged its cost.
- **`UnitOfWork`** (application) — distill's own, with `notes`, `cards` and `outbox`, mirroring `application/capture/ports.py`. **A handler never holds two modules' units of work.**

The two handlers are **adapters**, implementing the `OutboxHandler` protocol that already exists at `application/shared/outbox/ports.py` (`envelope_type` + `handle`) and dispatched by the existing `OutboxWorker`, which claims per handler type. A handler validates the payload and delegates to an application command handler; no distill logic lives under `adapters/`.

### Boundary rules against remember

Stated as prohibitions, so they are checkable rather than merely intended:

- `domain/distill/` and `application/distill/` import nothing from `domain/capture/` or `application/capture/`. The envelope payload is the only inbound channel.
- **No field on `Card` carries scheduling state** — no `due_at`, no algorithm state, no review counters. "Never scheduled" is the absence of a remember-side record, not a value here.
- Distill defines **no scheduling port**. When one exists it belongs to remember, and it must hide the algorithm's *state model* rather than rename it: a port exposing FSRS's stability/difficulty/retrievability would still break the domain on a swap to SM-2 or a Leitner box.
- Distill emits **no envelope announcing that cards were generated**. Remember wraps a card lazily on first encounter — a card with no remember-side record simply *is* a new card — which is what makes the deferral free rather than merely postponed, with no backfill left behind.
- **Notes are born only in capture.** Remember does not author notes; it opens capture mode and the ordinary approve → `note_approved` path runs. `note_approved` stays distill's only input.
- Remember's one write back is a card **rejection**, arriving as a *command into distill* rather than as a write into its stores, because the consumer of that negative signal is generation. It needs no new vocabulary: turning a card down during a review is a `user_audit` discard through the same command the audit surface already uses.

### Deliberately not decided here

The quote-matching rule; restoring a discarded card; query DTOs and list ordering; note versioning and amendment; regeneration; Notion publication; the scheduling port; the TUI shell (`tui-stack` territory — dispatcher, overlay behaviour, notifications).

### Naming

Capture's `Note` and distill's `Note` keep the same class name, disambiguated by module path. Renaming a shipped, tested aggregate buys readability at the cost of churn, and the codebase already namespaces by bounded context.

## Consequences

- **The grounding invariant is no longer enforced by construction.** It moved from "a card that exists is grounded" to "a card carrying no discard is grounded", which the type system cannot hold up. Every read over cards must exclude discarded ones, and a forgotten exclusion surfaces a fabricated card to the user during review — silently. This is the accepted cost of one relation and one repository port instead of two.
- A discard is terminal, so a card the person removes by mistake is gone. Restoring it would have to be conditional on the reason — an `ungrounded` card cannot come back without breaking the invariant — which is machinery bought against a mistake there is not yet a surface to make.
- The two-sided invariants are enforced at construction, so a proposal with an empty side, an over-long side, or two identical sides never becomes a card and leaves no discarded row behind. The audit trail therefore covers ungrounded proposals but not structurally invalid ones, which fail earlier and are visible only in whatever the generation adapter logs. The generous length bound narrows that hole rather than closing it.
- `discard` being a nullable value object rather than a status column pushes the filtering concern into every adapter: an in-memory store checks a field, a SQL store needs the mapping and index chosen so that "not discarded" stays a cheap predicate.
- A note's content exists in two rows in one store. With Notion deferred, module isolation is the sole justification; capture's row is the historical record of what a session produced, distill's is the artifact. They are not maintained against each other and nothing detects a divergence.
- Reusing capture's note id couples identity across modules. A future split into separate databases cannot renumber, and any change to how capture mints note ids propagates into distill silently.
- **A note can be stranded in `generating`.** The outbox retries a failed flashcard-gen until `max_attempts`, after which the envelope goes to `failed` and nothing moves the note's status. There is no timeout and no sweeper, so a permanently failing note reads as "in flight" forever in any surface that shows the status.
- The grounding invariant deletes work quietly. A model that paraphrases instead of quoting loses good cards; `discarded` rows preserve the signal, but nothing watches the discard rate — no threshold, no alert, and no surface for inspecting them.
- Only the quote is stored, so anchor resolution depends on the parser's behaviour forever. A parser change to how a block's text is produced can retroactively break resolution for cards written months earlier, with no stored fallback position.
- No run record exists, so there is no history of generation attempts. Regeneration will need one and will start with an empty history for every note that predates it.
- Two envelope types and two handlers serve a single branch. Retry granularity pays for that today; a reader who does not know the argument will reasonably read it as speculative machinery.
- Two classes named `Note` with different lifecycles sit in one codebase. The cost lands on whoever imports the wrong one, and only the module path prevents it.
- `backend-stack`'s Notion decision has no implementation path in the prototype, so the user cannot browse their notes outside Weles for as long as the deferral lasts.
- The boundary rules are conventions, not compiler-enforced. Nothing fails a build when a `due_at` appears on `Card`; they hold only as far as review and the layering tests reach.

## Alternatives Considered

1. **Keeping the earlier `decision.md` as this container's decision.** The status quo. Rejected by the user on the grounds that it went well past the shape of a domain — an adapter-level matching algorithm, read-model DTOs it declared out of scope in the same document, and two fields its own consequences called dead. Demoted to `frame.md` rather than deleted, because the material is a good input to this decision even where its conclusions overshot.
2. **Appending an `## Amendment` to that record** — schema-legal while the ADR is `open`, and the cheapest possible act. Rejected: the problem was not a missing scope correction but an over-committed decision, and an amendment can only add.
3. **A second, non-superseding ADR** holding the port contract and the boundary rules while the original kept the aggregate shapes. Rejected: it would leave two records disagreeing about how much is settled, and force every reader of the domain to reconcile them.
4. **`DiscardedProposal` as a third aggregate** with its own repository port — the earlier record's choice. Rejected: an aggregate and a port built for a reader that does not exist, since the duck session itself recorded the inspection endpoint as wanted "eventually, not now".
5. **Discarded proposals written only to a log.** The recommendation put to the user, on the grounds that a prototype does not need a queryable discard rate. Rejected by the user: the adapter writes to the database regardless, so the row exists either way and the question is only which relation holds it.
6. **A `rejected` status value reserved now** for remember's future user-rejection. Cut as dead vocabulary — nothing could set it, and every exhaustiveness check would gain a branch that cannot be exercised. The user then removed the need for it entirely: manual card removal is in scope today, so a review-time rejection is not a new state but the same `user_audit` discard arriving through the same command.
7. **`Note.version` pinned at `1`, with `Card.note_version` alongside it.** Insurance against a future amendment. Cut on the same grounds — the earlier record admitted it was "dead data until amendment exists", and its removal simplifies the generation idempotency key to `note_id` alone.
8. **One handler performing both the save and the generation.** The heaviest available cut, and defensible while only one branch exists. Rejected by the user: a redelivery after a failed model call would re-run the save, and a slow, expensive generation would be coupled to a fast local write.
9. **Capture enqueuing both envelopes up front.** Raised in the duck session. Rejected there: flashcard-gen would have nothing to read when its envelope arrives, creating an ordering problem the chain does not have.
10. **Anchor as character offsets into the note.** Precise and cheap to resolve. Rejected: models fabricate offsets far more readily than they misquote text, and an offset carries no way to detect that it is wrong.
11. **Anchor as a stored block or paragraph index.** The user's initial preference and the most direct route to a "jump to this block" gesture. Rejected: a stored index shifts silently to the wrong block when a paragraph is inserted above it, whereas a stored quote resolved at read time buys the same gesture, degrades loudly, and doubles as the fabrication check that makes the invariant enforceable at all.
12. **Fixing the matching rule in this decision** — normalizing against rendered block text, collapsing whitespace, stripping inline emphasis, requiring single-block resolution. Rejected as adapter behaviour: it constrains a parser that does not exist, and belongs to the change that writes one.
13. **An unresolvable anchor flagging the card as uncertain rather than discarding it.** Keeps every generated card and defers judgement to the user. Rejected: the note is the source of truth for its cards, which is what promotes the session's opening principle into the only enforced invariant the domain has.
14. **Cards generated from the session transcript**, or from the note with the transcript as grounding context. More context than a distilled note carries. Rejected on two counts: it forces either a much fatter envelope or a cross-module read into capture, and the note is what the user endorsed — material deliberately cut from the draft should not return as a card. The escape hatch, if quality disappoints, is minting a new envelope version with a richer payload, keeping the fix inside the outbox contract.
15. **A distinct id for distill's note plus a `source_note_id` reference.** The orthodox reading, keeping each module's identity its own. Rejected: it makes every cross-module conversation about "note X" ambiguous and forces an explicit uniqueness rule to recover idempotency that a shared id gives for free.
16. **Cards born into remember's domain, or wrapped by distill at generation time.** Rejected in favour of lazy wrapping: a card with no remember-side record already means "new", so eager wrapping would require an envelope with no consumer today or a backfill tomorrow.
17. **Query DTOs and list ordering decided here.** Rejected as read-model design driven by a shell this decision places out of scope; the aggregates above are what a query handler will read, and that is the whole of what the backend owes at this point.
18. **Renaming capture's `Note`** to remove the collision. Rejected: it churns a shipped, tested aggregate and its test suite for a readability gain module paths already mostly deliver.
19. **Keeping `status: active | discarded` alongside the `Discard` value object.** The shape this decision was first written with, and the one a reader expects. Rejected once the VO existed: the status is derivable from the VO's presence, so keeping both lets a card be discarded with no reason or reasoned with no status. An enum is easier to index; that cost is real and is recorded above, and it is an adapter's problem rather than the model's.
20. **Separate mechanisms for the two removals** — the system dropping an ungrounded proposal, the person deleting a card they do not want. The obvious reading, since one is validation and the other is a user gesture. Rejected on the user's own requirement that removal be one coherent mechanism: two paths would mean two places to get soft-deletion right, two shapes for the audit surface to merge, and a standing question about which one a review-time rejection uses.
21. **One undifferentiated discard, with no reason vocabulary.** Simplest, and enough to keep a card out of a review. Rejected: the two removals imply opposite corrections to generation, so a record that cannot tell them apart preserves the row and destroys the signal.
22. **`question` / `answer` as the card's two sides.** The vocabulary the generation port naturally produces, and more concrete than `front` / `back`. Rejected: it bakes one rhetorical form into the aggregate, and a term-to-definition or cloze card is the same two-sided artifact with no question in it. Nothing is built yet, so the rename costs nothing now and would be churn later.
23. **Bare `str` for the two sides**, with the aggregate doing the validation. Fewer types, and the rules are visible in one place. Rejected on the codebase's own convention: every meaningful string in `domain/capture/` is a frozen value object that canonicalizes and validates itself, and `Card` would be the only aggregate holding raw strings beside a `NoteContent` and an `Anchor`.
24. **Distinct `CardFront` and `CardBack` types.** Structurally identical but not interchangeable, so a swapped mapping fails to type-check. Rejected: the two share every rule and every constant, unlike the four capture wrappers whose separation is driven by differing limits; the only realistic swap is in the adapter that maps a proposal to a card, which is one place and covered by that port's contract test.
25. **A `CardContent` value object holding both sides**, carrying the pair invariant. Tempting because "the card's content" is then one thing a future amendment could replace atomically. Rejected: it buys one rule at the cost of an indirection on every read, and rendering always wants the two sides separately.
26. **A tight length bound on a card side**, enforcing brevity as a domain rule. Rejected: it converts a quality judgement into a construction failure, which is the one path that destroys the proposal instead of recording it — the opposite of what the discard mechanism exists for.
27. **Restoring a discarded card.** Raised against the terminal-discard rule: a person who deletes by mistake has no way back. Rejected for this version — restore has to be conditional on the reason, since an `ungrounded` card cannot return without breaking the invariant, and that is machinery for a mistake there is not yet a surface to make. Recorded as an accepted cost rather than resolved.
