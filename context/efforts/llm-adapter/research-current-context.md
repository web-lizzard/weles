---
date: 2026-09-11T20:42:00+02:00
topic: "Application ports that require LLM adapters"
topic_slug: current-context
container_id: llm-adapter
tags: [research, capture, distill, llm-adapters, hexagonal]
last_updated: 2026-09-11
---

# Research: Application ports that require LLM adapters

## Research Question

/research llm-adapter --topic wyciągnij mi z domeny/aplikacji wszystkie porty które musza mieć apdatery llm

(Resolved write: `research-current-context.md`; original `--topic` was not valid kebab-case.)

## Summary

The domain layer defines no LLM-facing ports — only repositories, scheduling (FSRS), and similar infrastructure. All generative-model seams live in the **application** layer as `Protocol` types. Today `backend/src/adapters/compose.py` wires **five** such protocols to deterministic in-memory adapters under `adapters/out/in_memory/`; there is no `adapters/out/llm/` package yet. Each port already has a contract-test suite parametrized for future LLM implementations (non-blocking CI cadence per `context/adrs/hexagonal-arch-shape/decision.md`).

## Findings

### Domain layer

- Repository and service ports in `backend/src/domain/capture/ports.py`, `backend/src/domain/distill/ports.py`, and `backend/src/domain/remember/ports.py` are persistence or algorithm ports (e.g. FSRS), not LLM adapter targets.
- `Embedding` in `backend/src/domain/capture/value_objects.py` is a value object returned by `EmbeddingPort`, not a port itself.

### Capture — conversation and vocabulary (four protocols)

- **`TopicExtractionPort`** — first user message → `SessionTopic`; consumed by `GenerateReplyCommand` when `session.topic` is unset (`backend/src/application/capture/commands/send_message.py:52-61`, `83-86`).
- **`ConfidenceAssessmentPort`** — transcript → `ConfidenceAssessment` for coverage/confidence on reply completion (`send_message.py:90-91`, `163-167`).
- **`ReplyGenerationPort`** — streaming `ReplyChunk` from transcript + assessment (`send_message.py:100-131`).
- **`EmbeddingPort`** — text → `Embedding` for topic/tag reuse-or-mint via `VocabularyResolver` (`backend/src/application/capture/services/vocabulary.py:13-14`, `37-39`), invoked from `GenerateReplyCommand` during draft chunks (`send_message.py:106-120`).

Definitions: `backend/src/application/capture/ports.py:21-36`.

In-memory adapters: `backend/src/adapters/out/in_memory/capture/` (`topic_extraction.py`, `confidence_assessment.py`, `reply_generation.py`, `embedding.py`).

Planned swap location (archived capture plan): `adapters/out/llm/capture/` — `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md`.

### Distill — card generation (one protocol)

- **`CardGeneration`** — `NoteContent` → `list[CardProposal]`; consumed by `GenerateCardsCommand` (`backend/src/application/distill/commands/generate_cards.py:23-27`, `41`), triggered asynchronously via `FlashcardGenHandler` (`backend/src/adapters/out/worker/handlers/flashcard_gen.py`).

Definition: `backend/src/application/distill/ports.py:9-10`.

In-memory adapter: `backend/src/adapters/out/in_memory/distill/card_generation.py`.

Documented as distill’s LLM seam: `context/adrs/distill-domain-shape/decision.md`.

### Composition and testing

- Wiring: `backend/src/adapters/compose.py` (~128 `_card_generation`; ~135-144 capture LLM ports + `VocabularyResolver`; ~200-204 `GenerateCardsCommand`; ~225-233 `GenerateReplyCommand`).
- Contract suites: `backend/tests/unit/capture/contracts/test_topic_extraction_contract.py`, `test_confidence_assessment_contract.py`, `test_reply_generation_contract.py`, `test_embedding_contract.py`; `backend/tests/unit/distill/contracts/test_card_generation_contract.py`.
- Stack intent: `pydantic-ai` in `backend/pyproject.toml`; no `pydantic_ai` imports in `backend/src` yet.

### Not LLM ports (common confusion)

- **`UnitOfWork`** in application `ports.py` — transaction boundary, not a model call.
- **`NoteFormat` / `NoteDocument`** — deterministic markdown grounding; retired **`NoteDocumentParser`** appears in ADR text but not in code (`grep` finds no `NoteDocumentParser` under `backend/`).
- **`TranscriptQueryPort`** — read path over the message store.
- **Semantic / meaning search** — mentioned in `context/foundation/project-overview.md`; no port in `backend/src` today.

### Effort container state

- `context/efforts/llm-adapter/effort.md` is a new effort with an empty Goal (no PRD yet); this document is the first consolidated port inventory for the effort.

## Code References

- `backend/src/application/capture/ports.py:21-22` — `TopicExtractionPort`
- `backend/src/application/capture/ports.py:25-26` — `ConfidenceAssessmentPort`
- `backend/src/application/capture/ports.py:29-32` — `ReplyGenerationPort`
- `backend/src/application/capture/ports.py:35-36` — `EmbeddingPort`
- `backend/src/application/distill/ports.py:9-10` — `CardGeneration`
- `backend/src/application/capture/commands/send_message.py:52-63` — `GenerateReplyCommand` LLM port injection
- `backend/src/application/capture/services/vocabulary.py:13-39` — `VocabularyResolver` uses `EmbeddingPort`
- `backend/src/application/distill/commands/generate_cards.py:23-41` — `GenerateCardsCommand` uses `CardGeneration`
- `backend/src/adapters/compose.py:128-144` — in-memory LLM stand-ins and vocabulary wiring
- `backend/src/adapters/compose.py:200-233` — command handler factories

## External References

- `context/adrs/hexagonal-arch-shape/decision.md` — `adapters/out/llm/`, InMemoryFirst, contract-test cadence for costly LLM adapters
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md` — three capture agent ports and `adapters/out/llm/capture/` target
- `context/archive/changes/2026-09-01-capture-flow-tag-dedup/research.md` — embedding port for reuse-or-mint
- `context/adrs/distill-domain-shape/decision.md` — `CardGeneration` as distill outbound seam
