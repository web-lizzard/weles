## Current State

Session closed. No open question about the flow itself remains. Carried forward, not for
this session to decide:

1. **Traceability.** Review, regeneration, merge, and the new discard reasons trace to no
   effort FR; the effort frame is closed and this frame cites, never mints. They are
   carried as Boundaries. Revisit only if the user wants an effort amendment.
2. **Machine fit (for /discover-contracts).** `StateMachine` assumes turns/events and a
   durable aggregate carrying the phase (`domain/shared/graph/machine.py:9-19,121-130`);
   distill's context is a transient run and every move is guard-determined, not
   model-chosen. Contract-shaping question.
3. **Roadmap drift.** S-06 prose ("single-shot", "without a transition graph") no longer
   describes this change — for `/roadmap`, not editable here.

## Log

### 2026-09-12 — graph-for-distill-flow: Distill's flow control lives in a domain graph — ACCEPTED

Why: user's rationale is placement, not persistence — without a graph the loop/threshold
heuristics become conditionals in `GenerateCardsCommand.handle()`
(`application/distill/commands/generate_cards.py:30-72`), while the effort requires
"the phases of an agent-driven flow and the legal moves between them" to be domain
artifacts testable without a model (effort `frame.md` FR-04). The change.md carry-over
leaned against a graph only because nothing needed to persist; persistence was the wrong
criterion given FR-04.
Consequence: roadmap S-06 prose ("without a transition graph") no longer describes this
change. Whether the vehicle is the existing `StateMachine` is left to contract shaping.
Supersedes: change.md "Leaning against a Graph/StateMachine" note.

### 2026-09-12 — single-invocation-run: Flow runs within one invocation, no persisted phase — ACCEPTED

Why: user confirmed no human turn sits between steps and nothing needs to survive a
separate request.

### 2026-09-12 — flow-recovery: Recovering an interrupted flow — PARKED

Why: user mentioned recovery as a possible later need; not required now and no current
consumer.

### 2026-09-12 — anchor-gate-before-review: Ungrounded proposals never reach review — ACCEPTED

Why: user decision; the deterministic check already exists
(`NoteDocument.locate`, `generate_cards.py:55-59`) and review spend on a card that is
discarded anyway buys nothing.

### 2026-09-12 — per-card-review-verdict: Model judges per card, domain decides pass/fail — ACCEPTED

Why: user decision; keeps the threshold policy in the domain and model-free testable
(effort FR-04), with the model supplying only the judgment.

### 2026-09-12 — merge-terminal: Merge removes model-judged duplicates and ends the flow — ACCEPTED

Why: user decision — duplicates are "cards that say the same thing", judged by a model;
merge is a terminal leaf.

### 2026-09-12 — review-vs-evaluation-scope: In-flow review vs effort's "LLM-as-judge out of scope" — OPEN

Why: effort frame excludes LLM-as-judge under Evaluation; needs explicit reading that
in-flow review is product behaviour, not evaluation.

### 2026-09-12 — slice-split: Should the flow land in-memory before going live — OPEN

Why: scope growth vs `context/foundation/rules/layering.md` InMemoryFirst and the
S-02 → S-05 precedent.

### 2026-09-12 — review-vs-evaluation-scope: In-flow review is product behaviour, not evaluation — ACCEPTED

Why: user confirmed. The effort's exclusion targets measuring instruction quality
(datasets, scores); in-flow review decides what is persisted.
Consequence: review verdicts are not Langfuse scores — tracing only, per the effort frame.
Supersedes: 2026-09-12 review-vs-evaluation-scope OPEN.

### 2026-09-12 — slice-split: Split the flow into an in-memory change before live — REJECTED

Why: user decision — S-02..S-05 already established the shared abstractions (graph,
instruction, tool), so distill is a second consumer rather than new ground. InMemoryFirst
still holds inside the slice: in-memory adapters for every new model task land here too.
Supersedes: 2026-09-12 slice-split OPEN.

### 2026-09-12 — regenerate-distinct-phase: Regeneration is its own phase, filling in rejected cards — ACCEPTED

Why: user decision — regeneration has a different task (replacements only, smaller scope)
and different context (review findings on weak cards + an accepted example), so it is a
different instruction and hence a different phase, not a re-entry into generation.
Strengthens graph-for-distill-flow.

### 2026-09-12 — review-rejection-discard: Review rejections persist as discards with model reasoning — ACCEPTED

Why: user decision; mirrors the existing discard pattern (`card_factory.py:40-58`) and
`Discard.detail` already carries free text (`value_objects.py:116-119`).

### 2026-09-12 — accepted-example-absent: Regeneration needs an accepted example that may not exist — OPEN

Why: zero accepted cards in round 1 leaves regeneration's required context unbuildable
under FR-05's guard (`domain/shared/instruction/model.py:102-114`).

### 2026-09-12 — accepted-example-absent: Accepted example is optional context — ACCEPTED

Why: user decision; a first round with no accepted card still regenerates, just without
the example. Keeps FR-05's guard satisfiable (the block is not required).
Supersedes: 2026-09-12 accepted-example-absent OPEN.

### 2026-09-12 — replacement-count-cap: Replacement count is instruction-steered, not domain-capped — ACCEPTED

Why: user decision ("miękko").
Consequence: the count is not provable without a model; only the instruction is pinned.

### 2026-09-12 — acyclic-flow: Flow is acyclic; merge is the only terminal step — ACCEPTED

Why: user observation — with merge as terminal leaf and at most one regeneration there
is no need for a loop; the flow simply runs forward to the end. The bound on
regeneration becomes structural (no edge back), checkable on the graph itself
(`Graph.terminal_states`, `reachable_from`, `domain/shared/graph/model.py:203-244`)
rather than a runtime counter guard.
Consequence: the review after regeneration is a distinct phase — the graph refuses
self-edges and an acyclic graph cannot re-enter the first review.

### 2026-09-12 — discard-reasons: Two new domain-fixed discard reasons: low quality, duplicate — ACCEPTED

Why: user decision; both review rejections and merge removals persist as discards,
extending `DiscardReason` (`domain/distill/value_objects.py:105-108`). Model reasoning
rides in `Discard.detail`; the reason set is never model-authored.

### 2026-09-12 — review-phase-reuse: Is the post-regeneration review the same phase as the first — OPEN

Why: user noted the second review is conditional too. Reusing one review phase
reintroduces a cycle bounded by a context guard; two phases keep the graph acyclic as the
body states. Needs an explicit choice.

### 2026-09-12 — review-phase-reuse: Review after regeneration is a separate phase — ACCEPTED

Why: user chose (A). Keeps the graph acyclic and the one-regeneration bound structural,
with no context guard counting rounds. Both review phases may share an instruction
builder; phase identity is not instruction identity.
Supersedes: 2026-09-12 review-phase-reuse OPEN.

### 2026-09-12 — second-review-scope: Second review judges replacements only — ACCEPTED

Why: user decision; round-1 verdicts stand, merge sees accepted cards from both reviews.

### 2026-09-12 — regeneration-threshold: Share of accepted vs note-length-tiered threshold — ACCEPTED

Why: user decision — share rather than count, threshold heuristic in a few tiers by note
length. Domain-held, model-free testable (effort FR-04).

### 2026-09-12 — duplicate-survivor: Better review verdict survives a duplicate pair; tie by date — ACCEPTED

Why: user decision. Tie direction (earlier vs later) still open.

### 2026-09-12 — empty-outcome: No surviving cards → note READY with zero cards — ACCEPTED

Why: user decision; an empty result is a completed flow, not a failure.

### 2026-09-12 — length-gate-before-review: Oversized proposals never reach review — ACCEPTED

Why: user decision — no tokens spent reviewing a card the length policy
(`domain/distill/card_factory.py:52-58`) already discards.

### 2026-09-12 — duplicate-survivor: Tie between equal verdicts goes to the replacement — ACCEPTED

Why: user decision — regeneration runs with a stronger instruction, so its card has a
better chance of being the better card. Explicitly a provisional heuristic. Round stands
in for creation time, which cannot separate cards minted in one round.
Supersedes: 2026-09-12 duplicate-survivor ACCEPTED (tie direction open).

### 2026-09-12 — gated-replacement: Gated-out proposals are replaced too — ACCEPTED

Why: user decision; a card discarded for unresolved anchor or excess length is as much a
gap as a review rejection. Regeneration receives the deterministic discard reason in
place of review findings.

### 2026-09-12 — graded-verdict: Review verdict is ordered, domain maps it to pass/fail — ACCEPTED

Why: user confirmed; required by "better verdict wins" in merge.

### 2026-09-12 — share-denominator: What the accepted share is measured against — OPEN

Why: with gated-out replacement accepted, a reviewed-only denominator can route a mostly
ungrounded round straight to merge, leaving gated cards unreplaced.

### 2026-09-12 — share-denominator: Accepted share is measured against all first-round proposals — ACCEPTED

Why: user chose the all-proposals option. A round that loses most cards at the anchor or
length gate falls below threshold and regenerates, which is the only way gated-out cards
get the replacements `gated-replacement` promises.
Supersedes: 2026-09-12 share-denominator OPEN.
