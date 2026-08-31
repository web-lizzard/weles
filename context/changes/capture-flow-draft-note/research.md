---
date: 2026-08-31T17:10:01+00:00
topic: "Domain-model requirements from the capture-flow-domain-shape ADR for capture-flow-draft-note"
topic_slug: null
container_id: capture-flow-draft-note
tags: [research, capture-flow, domain-model, note, topic, tag, capture-session]
last_updated: 2026-08-31
---

# Research: Domain-model requirements from the capture-flow-domain-shape ADR for capture-flow-draft-note

## Research Question

syntezuj mi wymagania modelowe z @context/adrs/capture-flow-domain-shape/ dla capture-flow-draft-note

## Summary

`capture-flow-draft-note` is slice **S-04** of the `capture-flow` effort roadmap, and per the roadmap's own acceptance-criteria assignment it owns only **AC-08** and **AC-09** — not AC-10/AC-11 (topic/tag dedup, assigned to S-05, which lists S-04 as a prerequisite) and not AC-12–AC-15 (showing the draft, conversational reshape, approval-gated outbox send, assigned to S-06, also prerequisite on S-04).

From `context/adrs/capture-flow-domain-shape/decision.md`, the model requirements that fall inside this scope are:

1. **`CaptureSession.draft_note(topic: Topic, content: str, tags: list[Tag]) -> Note`** — the entry point for note creation, guarded on `status == open`.
2. **A new `Note` aggregate** — `id`, `session_id`, `topic_id: UUID`, `content`, `tag_ids: list[UUID]`, `status` (`draft`/`approved`/`discarded`), `created_at`, `approved_at`, with a `draft(session_id, topic, content, tags) -> Note` factory called by `CaptureSession.draft_note()`.
3. **A new `Topic` aggregate** — `id`, `label`, `embedding`, `created_at`, factory `mint(label, embedding)`. This is the **note-level** topic: a distinct, richer fact from `CaptureSession.topic` (the raw string the user names at session start, AC-01), which the ADR deliberately keeps out of the reuse/embedding mechanism. AC-09's "can be more specific than the topic the user originally named" is exactly the gap between these two facts — both are required, neither replaces the other.
4. **A new `Tag` aggregate** — same shape as `Topic` (`id`, `label`, `embedding`, `created_at`, `mint()`). AC-08 requires the draft note to carry tags, so S-04 needs at least tag creation; the reuse-or-mint reconciliation logic itself (FR-009/FR-010) is explicitly assigned to US-05/S-05, which has S-04 as a prerequisite — see Open Questions.
5. **Vocabulary reconciliation lives outside the domain model** — the aggregates never see candidate strings, only already-resolved `Topic`/`Tag` objects; `Note` stores `topic_id`/`tag_ids`, not the objects themselves.
6. New repository ports are needed for `Note`, `Topic`, `Tag`, plus extension of the `UnitOfWork` port to carry `notes`, `topics`, `tags` alongside the existing `capture_sessions`, `messages`.

The existing codebase has none of this yet: `Note` and `Tag` don't exist at all, and the code's current `Topic` (`backend/src/domain/capture/value_objects.py:27`) is a plain string-wrapper that correctly represents `CaptureSession.topic` per the ADR's own design — it is not a duplicate or a naming bug, it is the session-level fact the ADR explicitly keeps separate from the note-level `Topic` aggregate. The only real friction is that Python needs two distinct classes where the ADR uses the same English word "Topic" for both concepts, so `/plan` needs to pick disambiguating names/modules rather than reconcile a design conflict. `CaptureSession` itself also currently diverges from the ADR's decided shape (`start()` takes no topic, topic is set later via `assign_topic()`; `draft_note()`/`approve()`/`close()` don't exist), so S-04 will touch `CaptureSession` as well as add the three new aggregates.

## Findings

### S-04 scope (roadmap / PRD / stories)

- Slice row: `S-04 | Users receive a drafted note and topic synthesized from the conversation | capture-flow-draft-note | in_progress` (`context/efforts/capture-flow/roadmap.md:14`).
- Full slice entry: outcome "Users receive a drafted note and topic synthesized from the conversation," acceptance criteria **AC-08, AC-09**, prerequisite **S-02** (`context/efforts/capture-flow/roadmap.md:56-62`).
- Dependency graph: `S-02 --> S-04`, `S-04 --> S-05` (topic/tag dedup), `S-04 --> S-06` (reshape & approve to outbox) (`context/efforts/capture-flow/roadmap.md:24-26`).
- AC-08: "At the end of the conversation, the agent produces a draft note with a topic, body, and tags derived from the discussion." (`context/efforts/capture-flow/stories.md:46`, under US-04, realizing FR-007/FR-008).
- AC-09: "The draft's topic can be more specific than the topic the user originally named, when the conversation supports it." (`context/efforts/capture-flow/stories.md:47`).
- AC-10/AC-11 (topic/tag reuse-or-mint) belong to US-05, realizing FR-009/FR-010, and are the acceptance criteria for **S-05**, not S-04 (`context/efforts/capture-flow/stories.md:49-56`; `context/efforts/capture-flow/roadmap.md:64-71`).
- AC-12–AC-15 (showing the draft, conversational reshape, approval gate, outbox send + session close) belong to US-06/US-07 and are the acceptance criteria for **S-06** (`context/efforts/capture-flow/stories.md:58-74`; `context/efforts/capture-flow/roadmap.md:73-80`).
- FR-008: "The session's topic label crystallizes over the course of the conversation; the agent may propose a more specific topic than the user's initial input for semantic precision." Priority: must-have (`context/efforts/capture-flow/prd.md:49`).
- Non-goals bearing on scope: session persistence/listing/resume is deferred to a future effort; a session always yields at most one note; flashcard generation and the "remember" review flow are separate flows (`context/efforts/capture-flow/prd.md:59-64`).
- S-01 (Socratic conversation) and S-02 (coverage wrap-up) are already `done` and archived; S-03 (abandon session) is `in_progress` in parallel with S-04's prerequisite chain (`context/efforts/capture-flow/roadmap.md:31-55,82-85`).

### Domain-model requirements from the ADR (scoped to S-04)

- `CaptureSession.draft_note(topic: Topic, content: str, tags: list[Tag]) -> Note` is the sole entry point for note creation, guarded on `status == open`, because "a note may only be drafted while the session is open" is knowledge only `CaptureSession` has (`context/adrs/capture-flow-domain-shape/decision.md:24`).
- `Note` fields and factory: `id`, `session_id`, `topic_id: UUID`, `content`, `tag_ids: list[UUID]`, `status` (`draft`/`approved`/`discarded`), `created_at`, `approved_at`; `draft(session_id, topic, content, tags) -> Note` (`context/adrs/capture-flow-domain-shape/decision.md:34-36`). Mutators (`update_content`, `change_topic`, `add_tag`, `remove_tag`) exist on the same aggregate but realize US-06 (S-06 scope), not AC-08/AC-09 directly (`decision.md:37`).
- `Topic` aggregate: `id`, `label`, `embedding`, `created_at`, factory `mint(label, embedding)` — "the note-level, reconciled topic that AC-08 and AC-09 require," distinct from `CaptureSession.topic` (`context/adrs/capture-flow-domain-shape/decision.md:46`).
- `CaptureSession.topic` is explicitly the raw, unreconciled user-named label from AC-01, and "deliberately does not participate in the reuse mechanism, because at session start there is nothing yet to reconcile against" (`context/adrs/capture-flow-domain-shape/decision.md:28`).
- The "note-level topic is a distinct fact from the session-level one, and neither can be dropped" is stated as the first of the three gaps this ADR closes over the prior duck-session summary (`context/adrs/capture-flow-domain-shape/decision.md:9`).
- `Tag` aggregate: same shape and factory pattern as `Topic` — `id`, `label`, `embedding`, `created_at`, `mint(label, embedding)` (`context/adrs/capture-flow-domain-shape/decision.md:48`).
- Vocabulary reconciliation (reuse-or-mint) is explicitly named as an application-service concern outside the aggregates, using an outbound similarity-search port; "the aggregates never see candidate strings or similarity scores, only already-resolved objects" (`context/adrs/capture-flow-domain-shape/decision.md:50`). FR-009/FR-010 (the reuse-or-mint rule itself) are realized by US-05/S-05, which has S-04 as a prerequisite.
- Operations take resolved objects; persisted state holds ids — `draft_note(topic: Topic, ..., tags: list[Tag])` extracts `topic_id`/`tag_ids` at the point of mutation (`context/adrs/capture-flow-domain-shape/decision.md:52`).
- Five repository ports are required in total for the capture-flow domain: `CaptureSession`, `Message`, `Note`, `Topic`, `Tag` (`context/adrs/capture-flow-domain-shape/decision.md:60`).

### Existing code vs. ADR shape (gap for S-04)

- `CaptureSession` (`backend/src/domain/capture/capture_session.py:9-27`): fields `id`, `topic: Topic | None`, `status`, `created_at`. `start()` (line 16) takes **no topic**; topic is set later via `assign_topic(topic: Topic)` (line 24), guarded to raise `SessionTopicAlreadyAssignedError` if already set. This diverges from the ADR's `start(topic: str)` class factory and lacks `draft_note()`, `approve()`, `close()` entirely.
- `Message` (`backend/src/domain/capture/message.py:13-33`) already matches the ADR shape exactly: immutable, append-only, `record(session_id, role, content)` factory, no sequence number.
- The existing `Topic` in `backend/src/domain/capture/value_objects.py:27` is a frozen string-wrapper (`value: str`) — it is the correct shape for `CaptureSession.topic` per the ADR's own design (a raw, non-reconciled label), not the ADR's `Topic` aggregate. `TopicExtractionPort` (`backend/src/application/capture/ports.py:9`) uses this same string-wrapper type.
- No `Note` class exists anywhere in `backend/src` or `backend/tests` (a `NoteNotFoundError` in `backend/tests/unit/test_exceptions.py:7` is an unrelated throwaway test fixture for exception-code derivation).
- No `Tag` class exists anywhere in the codebase.
- No `Topic` aggregate (id/label/embedding/`mint()`) exists; `grep -rn "def mint"` returns no hits.
- No `NoteRepository`, `TopicRepository`, or `TagRepository` port exists (`backend/src/domain/capture/ports.py:1-16` defines only `CaptureSessionRepository` and `MessageRepository`).
- `UnitOfWork` port (`backend/src/application/capture/ports.py:23-30`) currently exposes only `capture_sessions` and `messages`; no `notes`/`topics`/`tags` members.
- `InMemoryUnitOfWork` (`backend/src/adapters/out/in_memory/capture/unit_of_work.py:14-43`) wires only the two existing repositories; no in-memory Note/Topic/Tag adapters exist yet.
- `backend/tests/unit/capture/test_model.py` tests only the current `CaptureSession.start()`/`assign_topic()` and `Message.record()` behavior (e.g. `test_assign_topic_sets_topic_on_open_session` at line 34, `test_assign_topic_raises_when_topic_already_set` at line 43) against the pre-ADR shape; these will need revision once `CaptureSession.start(topic)`/`draft_note()` land.
- No test anywhere references `Note.draft`, `Topic.mint`, `Tag.mint`, or `draft_note` (`grep -rn` for each across `backend/tests/` returns no hits).

## Code References

- `context/efforts/capture-flow/roadmap.md:14,24-26,56-62` — S-04 slice row, dependency graph, full slice entry
- `context/efforts/capture-flow/prd.md:49,59-64` — FR-008 and Non-Goals bearing on scope
- `context/efforts/capture-flow/stories.md:46-47,49-56,58-74` — AC-08/AC-09 (US-04), AC-10/AC-11 (US-05), AC-12-AC-15 (US-06/US-07)
- `context/adrs/capture-flow-domain-shape/decision.md:9,24,28,34-38,46,48,50,52,60` — the decided aggregate shapes and reconciliation rules
- `backend/src/domain/capture/capture_session.py:9-27` — current `CaptureSession` shape (diverges from ADR)
- `backend/src/domain/capture/message.py:13-33` — current `Message` shape (matches ADR)
- `backend/src/domain/capture/value_objects.py:27` — current `Topic` value object (session-level string wrapper, not the ADR's note-level aggregate)
- `backend/src/domain/capture/ports.py:1-16` — existing repository ports (`Note`/`Topic`/`Tag` ports absent)
- `backend/src/application/capture/ports.py:9,23-30` — `TopicExtractionPort` and `UnitOfWork` port (no `notes`/`topics`/`tags` members yet)
- `backend/src/adapters/out/in_memory/capture/unit_of_work.py:14-43` — `InMemoryUnitOfWork`, wires only existing repos
- `backend/tests/unit/capture/test_model.py:34,43` — tests written against the pre-ADR `CaptureSession` shape
- `backend/tests/unit/test_exceptions.py:7` — unrelated throwaway `NoteNotFoundError` fixture

## Open Questions

- Whether S-04's `draft_note()` mints `Topic`/`Tag` naively (always new) with reuse-or-mint reconciliation added by S-05, or whether S-04 is expected to take already-resolved objects from day one (implying the reconciliation service/port lands as part of S-04 rather than S-05). The roadmap's AC assignment (AC-08/AC-09 only for S-04, AC-10/AC-11 for S-05) suggests the former, but the ADR's "operations take resolved objects" language doesn't by itself settle which slice builds the reconciliation service — `/plan` needs to decide.
- Naming/module strategy for having two ADR-named "Topic" concepts (the existing session-level string wrapper and the new note-level aggregate) coexist without a Python class-name collision.
- Whether `CaptureSession.start(topic: str)` replacing the current no-arg `start()` + `assign_topic()` is in scope for S-04, given S-01 (already archived/done) shipped against the current shape and its behavior/tests would need to change.
