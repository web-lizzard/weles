---
date: 2026-09-01T17:54:14+00:00
topic: "Required domain-model changes for capture-flow-tag-dedup (S-05)"
topic_slug: null
container_id: capture-flow-tag-dedup
tags: [research, capture-flow, domain-model, vocabulary-reconciliation, ports-and-adapters]
last_updated: 2026-09-01
---

# Research: Required domain-model changes for capture-flow-tag-dedup (S-05)

## Research Question

syntezuj wymagane zmiany w modelu domeny

## Summary

The capture-flow domain model (`Topic`, `Tag`, `Note`, `CaptureSession`) requires **no changes** for S-05. The ADR at `context/adrs/capture-flow-domain-shape/decision.md` deliberately keeps vocabulary reconciliation outside the domain layer, and the current aggregates already match that shape: `Note`/`CaptureSession` consume fully-resolved `Topic`/`Tag` objects and store only ids (`topic_id`, `tag_ids`); `Topic.mint()`/`Tag.mint()` need no change.

The real change surface is the seam between the domain-facing repository ports and the application service that already exists to construct vocabulary:

1. **Domain ports** (`backend/src/domain/capture/ports.py:27-36`) — `TopicRepository` and `TagRepository` currently expose only `add`/`get`-by-id. Both need a new method that performs the embedding-similarity search and returns the raw result — the closest existing row plus its similarity score, not a pre-thresholded match decision — e.g. `find_closest(embedding: Embedding) -> tuple[Topic, float] | None` (`None` only when the store is empty). The archived S-04 plan explicitly named this as S-05's addition: *"No `find_similar` — that is S-05's addition"* (`context/archive/changes/2026-08-31-capture-flow-draft-note/plan.md:203`).

2. **In-memory adapters** (`backend/src/adapters/out/in_memory/capture/{topic,tag}_repository.py:8-22`) — implement the new search method over the existing flat `dict[UUID, Model]`, computing similarity against every stored embedding and returning the closest one with its score. The adapter does **not** decide whether the match counts as "close enough" — it only returns data.

3. **Application service** (`backend/src/application/capture/services/vocabulary.py:12-22`) — `VocabularyResolver.resolve_topic`/`resolve_tag` currently mint and add unconditionally, with no lookup at all. This is the exact seam the S-04 plan names for rewrite: *"`VocabularyResolver` is introduced as the seam S-05 rewrites in place"* (plan.md:502, 504). The rewrite calls the new port method first; if the returned score clears a threshold, it reuses the existing `Topic`/`Tag` identity (no `mint`, no `add`); otherwise it mints and adds as today. **The reuse-or-mint decision — including the "close match" threshold from AC-10/AC-11 — belongs entirely to this application service, not to the port or the adapter.** This split matches the ADR's own wording precisely: *"an outbound port performs embedding-similarity search against existing rows, and an application service does the reuse-or-mint reconciliation"* (decision.md:50).

4. **No signature changes downstream.** `CaptureSession.draft_note()`, `Note.draft()`, and `GenerateReplyCommand.handle()` (`send_message.py:104-135`) already consume resolved `Topic`/`Tag` objects and need no changes. The SSE `draft_topic`/`draft_tag` events already fire after resolution, positioned specifically so that once reuse lands, the label shown reflects the existing row rather than the model's raw proposal (plan.md:72).

5. **Rejected alternative framing:** putting the threshold inside the adapter (`find_similar(embedding) -> Topic | None`, decided internally) was considered and rejected — it would smear a business rule (what counts as a close match) into infrastructure code that is supposed to be a dumb data-access layer, and would make the threshold untestable in isolation from a concrete adapter.

Zero code changes are needed to `UnitOfWork` — `topics`/`tags` are already first-class members of `InMemoryUnitOfWork`'s snapshot/restore rollback (`unit_of_work.py:49-64`), and the new port method is called through the same `uow.topics`/`uow.tags` attributes `VocabularyResolver` already receives.

## Findings

### Domain layer — no aggregate changes

- `Topic` (`backend/src/domain/capture/topic.py:8-21`) and `Tag` (`backend/src/domain/capture/tag.py:8-21`) are structurally identical `pydantic.BaseModel` aggregates: `id`, `label`, `embedding`, `created_at`, one `mint(label, embedding)` factory. No reconciliation logic inside either, and none is added by S-05 — reconciliation stays outside the domain per the ADR.
- `Note` (`backend/src/domain/capture/note.py:17-44`) stores `topic_id: TopicId` and `tag_ids: list[TagId]` (ids only), while its factory `Note.draft(session_id, topic: Topic, content, tags: list[Tag])` takes fully-resolved objects and derives the ids. No mutators exist on `Note` at all. Unaffected by S-05.
- `CaptureSession.draft_note(topic: Topic, content, tags: list[Tag])` (`capture_session.py:44-56`) delegates straight to `Note.draft`. Unaffected by S-05.

### Domain ports — the one domain-layer change

- `backend/src/domain/capture/ports.py:27-36` defines `TopicRepository` (`add`, `get`) and `TagRepository` (`add`, `get`) as `Protocol`s with no similarity/search capability today.
- Required addition: a method that performs embedding-similarity search and returns the closest candidate plus its score (or `None` when the store is empty), on both `TopicRepository` and `TagRepository`. The method does the search; it must not embed a "good enough" decision.
- Contract tests for both ports (`backend/tests/unit/capture/contracts/test_topic_repository_contract.py`, `test_tag_repository_contract.py`) currently only lock in add/get/overwrite semantics (lines 27-64 in each) and need a new case for the search method, parametrized the same way as the existing contract (currently a single-entry list — only the in-memory adapter).

### Adapters — implement the search, not the decision

- `backend/src/adapters/out/in_memory/capture/topic_repository.py:8-22` and `tag_repository.py:8-22` are flat `dict[UUID, Model]` stores with `add`/`get`/`snapshot`/`restore`. The new search method is added here, computing similarity over every stored embedding and returning the closest one with its score — no threshold logic in the adapter.

### Application layer — reuse-or-mint reconciliation

- `backend/src/application/capture/services/vocabulary.py:1-22` — `VocabularyResolver.resolve_topic`/`resolve_tag` currently: embed the label, `mint()`, `add()`, unconditionally — no lookup step exists. This is the only implementation (a concrete class, not a `Protocol`) and the plan is to rewrite it in place, not add a second implementation.
- `EmbeddingPort` (`backend/src/application/capture/ports.py:33-34`) already exists and is used by `VocabularyResolver` to produce embeddings; its in-memory adapter (`adapters/out/in_memory/capture/embedding.py:9-13`) is a deterministic SHA-512-hash-based synthetic embedding (8 dimensions) — not semantically meaningful, which matters when designing test fixtures for similarity behavior.
- `GenerateReplyCommand` (`backend/src/application/capture/commands/send_message.py:70-155`) calls `resolve_topic`/`resolve_tag` inline while streaming draft chunks (lines 104-107, 113) and needs no changes — it consumes whatever `Topic`/`Tag` objects `VocabularyResolver` returns, reused or newly minted alike.
- `InMemoryUnitOfWork` (`backend/src/adapters/out/in_memory/capture/unit_of_work.py:20-67`) already snapshots/restores `topics` and `tags` alongside `notes`/`messages`/`capture_sessions` for rollback (confirmed by `test_unit_of_work.py:83-113`). The reconciliation service composes with it exactly as `VocabularyResolver` does today — via `uow.topics`/`uow.tags` passed at call time, no new `UnitOfWork` shape needed.

### Explicit prior deferral to S-05

- `context/archive/changes/2026-08-31-capture-flow-draft-note/plan.md:51` — *"**Reuse-or-mint reconciliation** (FR-009/FR-010, AC-10/AC-11). S-04 always mints a fresh `Topic` and `Tag`. `VocabularyResolver` is introduced as the seam S-05 rewrites in place; no similarity-search port is added."*
- `plan.md:203` — *"No `find_similar` — that is S-05's addition."*
- `plan.md:502` — *"The ADR puts reconciliation in an application service so the aggregates never see candidate strings. In this slice the service always mints; S-05 rewrites its body to reuse-or-mint without touching any caller."*
- `plan.md:72` — SSE `draft_topic`/`draft_tag` events are emitted after `VocabularyResolver` resolution specifically so that "once reuse lands, the label shown in the TUI must be the existing row's label, not the one the model proposed."
- `context/adrs/capture-flow-domain-shape/decision.md:50` — pre-approves the target shape: *"an outbound port performs embedding-similarity search against existing rows, and an application service does the reuse-or-mint reconciliation — call the port per candidate label, reuse the existing row's identity on a match, else `mint(...)` on a miss."*

### No existing test coverage for reuse/dedup

- A repo-wide search for `dedup|reconcil|similar|cosine|nearest` across `backend/src` and `backend/tests` returns zero hits. No test constructs two topics/tags with the same or similar label and asserts they collapse to one id. This is entirely new surface, not a regression risk against a currently-green test.

## Code References

- `backend/src/domain/capture/topic.py:8-21` — `Topic` aggregate, `mint()` factory, no reconciliation logic.
- `backend/src/domain/capture/tag.py:8-21` — `Tag` aggregate, structurally identical to `Topic`.
- `backend/src/domain/capture/note.py:17-44` — `Note` stores `topic_id`/`tag_ids`; `draft()` factory takes resolved `Topic`/`Tag` objects.
- `backend/src/domain/capture/capture_session.py:44-56` — `CaptureSession.draft_note()` delegates to `Note.draft`.
- `backend/src/domain/capture/ports.py:27-36` — `TopicRepository`/`TagRepository`, currently `add`/`get` only; target of the new search method.
- `backend/src/adapters/out/in_memory/capture/topic_repository.py:8-22` — in-memory `TopicRepository` adapter, dict-backed.
- `backend/src/adapters/out/in_memory/capture/tag_repository.py:8-22` — in-memory `TagRepository` adapter, dict-backed.
- `backend/src/application/capture/services/vocabulary.py:1-22` — `VocabularyResolver`, the seam S-05 rewrites: currently unconditional mint+add.
- `backend/src/application/capture/ports.py:33-34` — `EmbeddingPort`.
- `backend/src/adapters/out/in_memory/capture/embedding.py:9-13` — `DeterministicEmbeddingAdapter`, synthetic SHA-512-based embedding, 8 dimensions.
- `backend/src/application/capture/commands/send_message.py:70-155` (calls at 104-107, 113, 131-135) — `GenerateReplyCommand`, calls `VocabularyResolver`, builds the note; needs no changes.
- `backend/src/adapters/out/in_memory/capture/unit_of_work.py:20-67` — `InMemoryUnitOfWork`, already snapshots/restores `topics`/`tags`.
- `backend/tests/unit/capture/contracts/test_topic_repository_contract.py:12-64` — current `TopicRepository` contract, add/get/overwrite only.
- `backend/tests/unit/capture/contracts/test_tag_repository_contract.py:12-63` — current `TagRepository` contract, add/get/overwrite only.
- `backend/tests/unit/capture/test_unit_of_work.py:83-113` — rollback/commit tests covering `notes`/`topics`/`tags`.
- `context/adrs/capture-flow-domain-shape/decision.md:50` — target shape: port does search, application service does reuse-or-mint reconciliation.
- `context/archive/changes/2026-08-31-capture-flow-draft-note/plan.md:51,72,203,502,504` — explicit deferral of reconciliation to S-05, and the exact seam (`VocabularyResolver`) it names for rewrite.
- `context/efforts/capture-flow/roadmap.md:15,64-71` — S-05 slice definition: AC-10, AC-11, prerequisite S-04.
- `context/efforts/capture-flow/prd.md:69` — open question on what counts as a "close match" (exact label vs. similarity threshold), unresolved, owned by `/plan`.

## Open Questions

- Exact similarity metric and threshold for "close match" (cosine distance? what cutoff?) — PRD leaves this to `/plan` (`prd.md:69`).
- Exact port method signature and name (`find_closest`, `search_similar`, etc.) and whether it returns a single closest candidate or a ranked list — this document settles the *shape* (raw score returned, decision made in `VocabularyResolver`) but not the final name/arity, left to `/plan`.
- Whether `DeterministicEmbeddingAdapter`'s synthetic hash-based embeddings can meaningfully exercise similarity-threshold behavior in tests, or whether test fixtures need deliberately controlled embeddings.
