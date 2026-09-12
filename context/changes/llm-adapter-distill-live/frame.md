---
status: closed
created: 2026-09-12
updated: 2026-09-12
---

## Boundaries

**In scope.**

Distill's card generation is a flow of steps rather than a single model call: cards are
generated, reviewed, conditionally generated and reviewed again, and finally merged. Merge
is the terminal step; nothing follows it.

The flow has no cycle. Every route through it ends at merge, and merge is its only
terminal step. Generation is repeated at most once, and that bound is a property of the
flow's shape — there is no move back to an earlier step — not a count kept at runtime.

Review after repeated generation is a step of its own, not a return to the first review.
It is reached only through repeated generation, and its only successor is merge. It judges
only the replacements; the first review's verdicts stand.

The flow's control policy — which step follows which, when generation is repeated, and when
the flow ends — is held in the domain as phases and legal moves, not as branching inside
the application command. The application invokes the flow; it does not decide its route.

A flow runs to completion within one card-generation invocation. No phase of it is
persisted between steps, and nothing about it has to survive a separate request.

A card proposal whose anchor does not resolve against the note, or that breaches the card
length policy, never reaches review.

Review is a model's judgment made per card, on an ordered scale rather than pass or fail.
Whether a card passes is decided by the domain from that judgment, not by the model; whether the batch as a whole is good enough to end
generation is likewise a domain decision: generation is repeated when the share of
first-round proposals that review accepted falls below a threshold. The share is measured
against every proposal of the round, including those discarded before review, so a round
that loses cards at the deterministic checks counts those losses. The threshold depends on the note's length, in a
small number of heuristically set tiers.

Review inside the flow is product behaviour, not evaluation: its verdict decides what is
kept. It is therefore not excluded by the effort's evaluation boundary, and its verdicts
are not recorded as evaluation scores — Langfuse sees them as traces only.

Repeated generation is a phase of its own, distinct from first generation. It produces
replacements only for the cards that did not survive the first round — those review
rejected and those discarded before review for an unresolved anchor or excess length —
not a new batch. It is told why each of those cards failed (review's findings, or the
deterministic discard reason) and, when review accepted any card, an example of one. A
first round with no accepted card still proceeds to repeated generation, without the
example. How many replacements to produce is asked of the model; the domain does not cap
it.

A card review rejects is kept as a discarded card for low quality, whose detail carries
the model's reasoning for the rejection. A card merge removes is kept as a discarded card
for duplicating another card's meaning. These are two new discard reasons, beside the
deterministic ones that already discard ungrounded and oversized proposals; the set of
reasons is fixed by the domain, never authored by the model.

Merge removes cards a model judges to say the same thing as another card in the batch.
It considers the cards accepted by either review. Of two cards that say the same thing,
the one with the better review verdict survives; between equal verdicts, the replacement
survives over a first-round card. This tie rule is a heuristic, expected to change.

A flow in which no card survives still completes: the note ends ready with no cards, not
failed.

The whole flow — its phases, every model-facing task in it, and both their in-memory and
real-provider adapters — lands in this one change.

**Out of scope.**

Recovering or resuming an interrupted flow. A later change may add it; nothing here needs
to foreclose it, and nothing here provides it.

## Requirements

- **FR-04** (effort `llm-adapter`) — applies to distill's generation flow.
- **FR-05** (effort `llm-adapter`) — applies to every model-facing task of the flow.
- **FR-08** (effort `llm-adapter`) — the distill half.
- **FR-09** (effort `llm-adapter`) — the distill half.
