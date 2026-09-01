# Topic and Tag Deduplication Through Reuse — Implementation Plan

## Overview

Slice S-05 of the `capture-flow` effort. Today every drafted note mints a brand-new `Topic` and a brand-new `Tag` per proposed label, so a user who captures the same subject twice ends up with two semantically identical vocabulary rows. This slice makes the drafting path check the existing vocabulary first and reuse a close match instead of minting a near-duplicate, and makes that reuse visible to the user. It realizes AC-10 (an existing topic or tag that closely matches is reused) and AC-11 (a new tag is minted only when nothing is a close match, and the user is shown it when that happens).

Execution state for this plan lives in `todos.md`, sibling of this file.

The distinguishing decision of this plan is **where the matching rule lives**. The upstream research proposed leaving similarity scoring in the outbound port and the reuse-or-mint decision in the application service. This plan instead puts the *criteria* — the metric and the threshold — in the domain as a value object, keeps the *orchestration* in the application service, and reduces the port to plain candidate retrieval. The domain gains a real rule it can state and test with no adapter in sight; the ADR's "reconciliation lives outside the domain model" stays intact, because the domain still never mints, never persists, and never sees a candidate string.

## Current State Analysis

- `Topic` (`backend/src/domain/capture/topic.py:8-21`) and `Tag` (`backend/src/domain/capture/tag.py:8-21`) are structurally identical aggregates — `id`, `label`, `embedding`, `created_at`, one `mint()` factory. Both already carry the embedding a similarity comparison needs.
- `TopicRepository` and `TagRepository` (`backend/src/domain/capture/ports.py:27-36`) expose only `add`/`get`-by-id. There is no way to ask either store what it already holds.
- `VocabularyResolver` (`backend/src/application/capture/services/vocabulary.py:12-22`) embeds the label, mints, and adds — unconditionally, with no lookup step at all. The archived S-04 plan introduced it explicitly as the seam this slice rewrites (`context/archive/changes/2026-08-31-capture-flow-draft-note/plan.md:502`, `:504`) and recorded that no similarity port was added yet (`:203`).
- `GenerateReplyCommand` (`backend/src/application/capture/commands/send_message.py:104-115`) calls `resolve_topic`/`resolve_tag` mid-stream and emits `DraftTopicEvent`/`DraftTagEvent` immediately afterwards, positioned so that the label shown is the resolved one rather than the model's raw proposal.
- `InMemoryUnitOfWork` (`backend/src/adapters/out/in_memory/capture/unit_of_work.py:20-67`) already snapshots and restores `topics` and `tags`, so rollback needs no new work.
- No dedup coverage exists anywhere — a repo-wide search for `dedup|reconcil|similar|cosine|nearest` returns zero hits across `backend/src` and `backend/tests`. This is entirely new surface, not a regression risk.
- `Settings` (`backend/src/config/settings.py:6-14`) is a `pydantic-settings` model with `env_file=".env"` and `extra="forbid"`, holding `database_url` (required) and `notion_api_token`. It is **not instantiated anywhere in `src/`** today — only in `backend/tests/unit/test_settings.py`.
- `backend/tests/features/capture-flow/` holds feature files for US-01, US-02 and US-04. There is none for US-05, and `[tool.pytest.ini_options].markers` registers `AC-01` through `AC-09` only.

### Key Discoveries:

- **`DeterministicEmbeddingAdapter` is numerically unusable for any similarity metric as written.** `backend/src/adapters/out/in_memory/capture/embedding.py:12` does `struct.unpack(">8d", sha512_digest)` — reinterpreting random bytes as IEEE-754 doubles. Measured over the labels this flow actually produces, components land anywhere from `1e-272` to `1e297`, so a naive `sqrt(sum(x*x))` magnitude overflows to `inf` for **every** label, and a naive cosine returns `0.0` or `NaN` for every pair. Dedup would silently never fire. Both the metric and the adapter have to be fixed.
- **Dimension 8 is too narrow even after the adapter is fixed.** Measured over 19,900 pairs of unrelated labels with bytes scaled into `[-1, 1]`: at 8 dimensions 0.503% of unrelated pairs exceed a 0.85 cosine (max observed 0.9515) — a real false-merge rate; at 32 dimensions the maximum observed similarity between unrelated labels is 0.6459, with zero pairs above 0.85. The SHA-512 digest supplies 64 bytes, so 32 dimensions is free.
- **Cosine of a vector with itself computes to `1.0000000000000002` in floating point**, which a naive `[-1.0, 1.0]` validator rejects. The result has to be clamped into range before it becomes a `SimilarityScore`.
- **`chat.ts:107` overwrites `draft.tags` wholesale on `draft_done`** with plain label strings. A `reused` flag carried only on the streaming events is destroyed by the final event unless the store deliberately preserves it.
- **`compose.py` is imported by `src/adapters/http/capture.py:8` and by `backend/tests/integration/support/in_memory_capture.py:5`.** Making it the first production `Settings()` consumer means importing either module starts requiring `DATABASE_URL`.
- **The exception-mapping exhaustiveness test walks `CoreException.__subclasses__()` recursively** (`context/foundation/rules/exceptions.md`), so every new exception must gain an `EXCEPTION_STATUS_MAP` entry in the same phase or the suite goes red.
- `tests/bdd/test_features.py:7-11` registers step modules explicitly in `pytest_plugins`; a new step module that is not listed there never loads its scenarios.
- The S-04 plan wrote its own acceptance scenarios in-plan (its Phase 10) rather than delegating to `/bdd`. This plan follows that precedent.

## Desired End State

A user who captures a second note about a subject they have already captured gets the *existing* topic and tag rows attached to the new note — same ids, same labels — instead of fresh near-duplicates, and the TUI marks which tags were newly minted and which were reused. The matching rule is a domain value object that can be constructed and asserted against with no repository, no adapter and no `UnitOfWork`, and its threshold is an environment-tunable setting rather than a committed constant.

Verify by running the backend and TUI, holding two short capture sessions that reach a draft with the same conversation, and observing that the second draft's tags are marked as reused rather than new. Automated verification is the AC-10/AC-11 acceptance scenarios plus the unit, contract and integration suites.

## What We're NOT Doing

- **Changing the `Topic`, `Tag`, `Note`, `Message` or `CaptureSession` aggregates.** They already hold everything this slice needs; `Note` still stores `topic_id`/`tag_ids` and still receives resolved objects.
- **Touching `CaptureSession.topic`.** The ADR is explicit that the session-level label is raw user input and deliberately does not participate in reuse, because at session start there is nothing to reconcile against.
- **Changing `DraftDoneEvent`.** Turning its `tags: list[str]` into a richer shape is a breaking change for every current consumer, and the draft-review surface it would serve is AC-12, which belongs to S-06.
- **Introducing a semantically meaningful embedding adapter.** `DeterministicEmbeddingAdapter` is repaired to be numerically well-formed, not made to understand language. A real embedding provider is its own slice, and `layering.md`'s InMemoryFirst rule wants the behavior proven against the in-memory adapter first.
- **Exact-label or case-insensitive matching as a second path.** The criterion is cosine similarity alone. With hash-based embeddings this means `"python"` and `"Python"` will *not* merge — see Open Risks.
- **Pushing the threshold into the port or the adapter.** Rejected in research (`research.md:30`) and rejected again here: a business rule inside a data-access layer cannot be tested without a concrete adapter.
- **Lazy reconstruction of `Topic`/`Tag` from stored ids.** The ADR names the mechanism as unspecified and leaves it to planning; nothing in this slice needs it.
- **Amending `capture-flow-domain-shape`.** The chosen split keeps reconciliation — the reuse-or-mint act — in the application service, so `adr_refs` stays `kinds: [implements]`.

## Implementation Approach

Four layers, in dependency order, each as a stubs phase followed by a behavior phase.

**Domain** gains a `SimilarityScore` value object, a `cosine_similarity` method on `Embedding`, and a `MatchCriteria` value object holding a threshold, whose `best_match` picks the highest-scoring candidate above that threshold and breaks ties on the older `created_at`. `MatchCriteria` is generic over a `TypeVar` constrained to `Topic | Tag`, so the one rule serves both vocabularies without the aggregates themselves merging — consistent with the ADR's accepted duplication of the two types.

**Ports and adapters** gain `candidates()` on `TopicRepository`/`TagRepository`, returning the stored rows with their embeddings and no scoring whatsoever. The adapter stays a dumb data-access layer, which is exactly why the metric can live in the domain. `DeterministicEmbeddingAdapter` is repaired in the same pair.

**Application** rewrites `VocabularyResolver` to embed, retrieve candidates, ask `MatchCriteria`, and either reuse the match's entry or mint-and-add. It returns `ResolvedTopic`/`ResolvedTag`, each carrying the entry plus a `reused` flag, which `GenerateReplyCommand` forwards into the SSE events. The threshold arrives as `Settings.vocabulary_match_threshold` and is turned into a `MatchCriteria` in `compose.py`.

**TUI** parses the new flag, preserves it across the `draft_done` overwrite, and renders newly minted tags distinctly from reused ones.

## Critical Implementation Details

`Embedding.cosine_similarity` must divide both vectors by their largest absolute component before computing the dot product and norms — the deterministic adapter's raw components overflow `x*x` to `inf`, and a naive implementation returns `0.0` or `NaN` for every real pair without failing loudly. It must also clamp the final quotient into `[-1.0, 1.0]`, because a vector compared against itself computes to `1.0000000000000002`.

Reuse within a *single* draft falls out for free and must not be broken: `VocabularyResolver` adds each newly minted row through `uow.tags` before the next `DraftTagChunk` is resolved, so a second near-identical tag proposed in the same stream already sees the first as a candidate.

## Phase 1: Domain vocabulary matching — stubs

### Overview

Materializes every domain symbol the next phase's tests import: the score value object, the criteria value object, the match wrapper, the metric's signature, and the three new exceptions. No behavior.

### Changes Required:

#### 1. `SimilarityScore` and the metric signature

**File**: `backend/src/domain/capture/value_objects.py`

**Intent**: A similarity score is a bounded quantity, not a bare float, and the metric belongs on `Embedding` so it exists in exactly one place for both vocabularies.

**Contract**: `SimilarityScore(BaseModel, frozen=True)` with `value: float`, following the frozen-`BaseModel` pattern the module already uses; a `model_validator` slot for the `[-1.0, 1.0]` range check. `Embedding` gains `def cosine_similarity(self, other: "Embedding") -> SimilarityScore:` raising `NotImplementedError`.

#### 2. New exceptions

**File**: `backend/src/domain/capture/exceptions.py`

**Intent**: One exception per invariant the next phase enforces.

**Contract**: `SimilarityScoreOutOfRangeError`, `EmbeddingDimensionMismatchError`, `ZeroMagnitudeEmbeddingError`, all `CoreException` subclasses, yielding codes `similarity_score_out_of_range`, `embedding_dimension_mismatch`, `zero_magnitude_embedding`.

#### 3. `MatchCriteria` and `VocabularyMatch`

**File**: `backend/src/domain/capture/vocabulary.py` (new)

**Intent**: The reuse rule stated in the domain's own vocabulary — what counts as close enough, and which candidate wins — expressible and assertable without any repository, adapter or `UnitOfWork`.

**Contract**: A `TypeVar` constrained to the two vocabulary aggregates, a generic match wrapper, and the criteria object. Written out because every later phase depends on these exact signatures:

```python
VocabularyEntryT = TypeVar("VocabularyEntryT", Topic, Tag)


class VocabularyMatch(BaseModel, Generic[VocabularyEntryT], frozen=True):
    entry: VocabularyEntryT
    score: SimilarityScore


class MatchCriteria(BaseModel, frozen=True):
    threshold: SimilarityScore

    def best_match(
        self,
        target: Embedding,
        candidates: Sequence[VocabularyEntryT],
    ) -> VocabularyMatch[VocabularyEntryT] | None: ...
```

The `TypeVar` is value-constrained to `Topic`/`Tag` rather than bound to a `Protocol` so the generic model stays a validatable pydantic type.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green (existing suites unaffected)
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean

---

## Phase 2: Domain vocabulary matching — behavior

### Overview

Implements the range validator, the overflow-resistant cosine metric, and the selection rule, and registers the three new exception codes.

### Changes Required:

#### 1. `SimilarityScore` validation

**File**: `backend/src/domain/capture/value_objects.py`

**Intent**: Make an out-of-range score unrepresentable, so a misconfigured threshold fails at construction rather than silently disabling or forcing reuse.

**Contract**: `model_validator(mode="after")` raising `SimilarityScoreOutOfRangeError` when `value` is outside `[-1.0, 1.0]` or is not finite.

#### 2. `Embedding.cosine_similarity`

**File**: `backend/src/domain/capture/value_objects.py`

**Intent**: The one place the metric exists. It has to survive the deterministic adapter's extreme component magnitudes rather than quietly returning nonsense.

**Contract**: Raises `EmbeddingDimensionMismatchError` when the two embeddings differ in length, and `ZeroMagnitudeEmbeddingError` when either has no non-zero component. Otherwise divides each vector by its largest absolute component before computing dot product and norms, then clamps the quotient into `[-1.0, 1.0]` and returns a `SimilarityScore`. The scaling and clamping are both load-bearing — see Critical Implementation Details.

#### 3. `MatchCriteria.best_match`

**File**: `backend/src/domain/capture/vocabulary.py`

**Intent**: The reuse rule: closest wins, ties go to the older row, nothing below the threshold ever wins.

**Contract**: Scores every candidate against `target`, discards those scoring strictly below `threshold`, and returns the highest-scoring survivor wrapped in a `VocabularyMatch`. Equal scores are broken by the earlier `created_at`. Returns `None` for an empty candidate list and for a list where nothing clears the threshold. Total and deterministic — the same store always yields the same answer.

#### 4. Exception mapping

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Keep the exhaustiveness test green; the three new codes are all malformed-input conditions.

**Contract**: `similarity_score_out_of_range`, `embedding_dimension_mismatch` and `zero_magnitude_embedding` added to `EXCEPTION_STATUS_MAP`, each mapped to 422.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture -v` green
- `cd backend && uv run pytest` green
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean

---

## Phase 3: Candidate retrieval and embedding conditioning — stubs

### Overview

Adds the retrieval half of the mechanism to both repository ports and their in-memory adapters. No scoring anywhere in this layer.

### Changes Required:

#### 1. Repository ports

**File**: `backend/src/domain/capture/ports.py`

**Intent**: Give the application service a way to ask a store what it holds, without teaching the store anything about what counts as a match. This is the retrieval/decision split that keeps the threshold testable in isolation.

**Contract**: `TopicRepository` gains `async def candidates(self) -> list[Topic]: ...`; `TagRepository` gains `async def candidates(self) -> list[Tag]: ...`. Named for what it returns to the caller, not for a search it does not perform.

#### 2. In-memory adapters

**File**: `backend/src/adapters/out/in_memory/capture/topic_repository.py`, `backend/src/adapters/out/in_memory/capture/tag_repository.py`

**Intent**: Materialize the method so the next phase's contract tests can import and call it.

**Contract**: `candidates()` on both, raising `NotImplementedError`.

#### 3. Embedding adapter dimension constant

**File**: `backend/src/adapters/out/in_memory/capture/embedding.py`

**Intent**: Name the widened dimension ahead of the behavior change that uses it.

**Contract**: `_EMBEDDING_DIMENSION` raised from 8 to 32; `embed()` body untouched in this phase.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean

---

## Phase 4: Candidate retrieval and embedding conditioning — behavior

### Overview

Implements `candidates()` on both adapters and repairs `DeterministicEmbeddingAdapter` so its output is numerically usable by the metric Phase 2 built.

### Changes Required:

#### 1. `candidates()` implementations

**File**: `backend/src/adapters/out/in_memory/capture/topic_repository.py`, `backend/src/adapters/out/in_memory/capture/tag_repository.py`

**Intent**: Return the stored rows, nothing more.

**Contract**: `list(self._topics.values())` / `list(self._tags.values())` — an empty list for an empty store, one entry per stored id, and an overwritten id appearing once with its latest value.

#### 2. Port contract tests

**File**: `backend/tests/unit/capture/contracts/test_topic_repository_contract.py`, `backend/tests/unit/capture/contracts/test_tag_repository_contract.py`

**Intent**: `contract-testing.md` requires one behavioral contract suite per port, parametrized over implementations. The new method joins the existing add/get/overwrite cases in the same parametrized shape.

**Contract**: Cases asserting an empty store yields `[]`, that every added row is present, and that a second `add` with the same id leaves one entry carrying the updated value.

#### 3. `DeterministicEmbeddingAdapter` conditioning

**File**: `backend/src/adapters/out/in_memory/capture/embedding.py`

**Intent**: The adapter must produce vectors a cosine can actually compare. Reinterpreting digest bytes as IEEE-754 doubles yields components up to `1e297`; scaling bytes into `[-1, 1]` yields well-conditioned vectors while staying deterministic and semantics-free.

**Contract**: `embed()` maps the first 32 digest bytes to floats via `(byte - 127.5) / 127.5`, replacing the `struct.unpack` reinterpretation. Determinism, stable dimension, and distinctness for distinct inputs — the three properties the existing contract at `backend/tests/unit/capture/contracts/test_embedding_contract.py:14-47` already asserts — are all preserved. A new contract case asserts every component is finite and within `[-1.0, 1.0]`.

#### 4. `UnitOfWork` rollback coverage

**File**: `backend/tests/unit/capture/test_unit_of_work.py`

**Intent**: `candidates()` is the first method that can observe rolled-back rows, so the existing snapshot/restore guarantee needs an assertion through the new door.

**Contract**: A case asserting that a topic and a tag added inside an uncommitted `UnitOfWork` block do not appear in `candidates()` afterwards.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/contracts -v` green
- `cd backend && uv run pytest` green
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean

---

## Phase 5: Reuse-or-mint, stream contract and configuration — stubs

### Overview

Materializes the application-layer symbols the next two phases need: the resolver's new return types and constructor, the SSE flag, and the settings field.

### Changes Required:

#### 1. Resolution value objects

**File**: `backend/src/application/capture/value_objects.py`

**Intent**: The caller needs to know not just *which* topic or tag it got, but whether it was reused — AC-11 requires the newly minted case to be visible to the user, and nothing downstream can reconstruct that fact after the resolver returns.

**Contract**: `ResolvedTopic(BaseModel, frozen=True)` with `topic: Topic` and `reused: bool`; `ResolvedTag(BaseModel, frozen=True)` with `tag: Tag` and `reused: bool`.

#### 2. `VocabularyResolver` signature

**File**: `backend/src/application/capture/services/vocabulary.py`

**Intent**: The criteria are injected, not constructed in place, so the threshold's source stays a composition-root concern and tests can pin it.

**Contract**: `__init__(self, embedding: EmbeddingPort, criteria: MatchCriteria)`. `resolve_topic(label, topics) -> ResolvedTopic` and `resolve_tag(label, tags) -> ResolvedTag`, bodies still unconditional mint-and-add wrapped in the new types with `reused=False`.

#### 3. SSE event flag

**File**: `backend/src/application/capture/dto.py`

**Intent**: Carry the reuse fact to the client on the events that already announce each resolved label.

**Contract**: `DraftTopicEvent` and `DraftTagEvent` each gain `reused: bool`. `DraftDoneEvent` is deliberately unchanged.

#### 4. Threshold setting

**File**: `backend/src/config/settings.py`

**Intent**: Put the tuning knob where changing it costs an environment variable rather than a commit. The number is a deployment concern, not a domain constant.

**Contract**: `vocabulary_match_threshold: float = 0.85`, overridable through `VOCABULARY_MATCH_THRESHOLD`. Defaulted rather than required — `database_url` is the only mandatory setting today, and making this one mandatory would break every existing environment.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean

---

## Phase 6: Reuse-or-mint, stream contract and configuration — behavior

### Overview

Rewrites the resolver into reuse-or-mint, forwards the flag into the stream, and wires the threshold from settings through the composition root.

### Changes Required:

#### 1. `VocabularyResolver` reuse-or-mint

**File**: `backend/src/application/capture/services/vocabulary.py`

**Intent**: The reconciliation the ADR places in an application service: ask the domain rule, reuse on a hit, mint on a miss. The service orchestrates; it does not decide what "close" means.

**Contract**: Each `resolve_*` embeds the label, calls `candidates()` on the passed repository, and hands both to `MatchCriteria.best_match`. On a match it returns the matched entry with `reused=True` and performs **no** `mint` and **no** `add`. On `None` it mints, adds, and returns `reused=False`. The label of a reused entry is the stored row's label, not the one just proposed.

#### 2. Command wiring

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Forward the flag onto the events that already exist, without disturbing the ordering S-04 established.

**Contract**: The `DraftTopicChunk` and `DraftTagChunk` branches unwrap `ResolvedTopic`/`ResolvedTag`, keep the resolved aggregate for `session.draft_note(...)`, and pass `reused` into `DraftTopicEvent`/`DraftTagEvent`. Event order and the `DraftTopicMissingError` guard are unchanged.

#### 3. Composition root

**File**: `backend/src/adapters/compose.py`

**Intent**: Turn the configured float into the domain value object once, at startup, where a bad value fails loudly.

**Contract**: A module-level `Settings()` instance; `VocabularyResolver(_embedding, MatchCriteria(threshold=SimilarityScore(value=_settings.vocabulary_match_threshold)))`. `SimilarityScore`'s validator makes an out-of-range environment value an import-time failure rather than a silently broken dedup. This makes `compose.py` the first production `Settings()` consumer — see Migration Notes.

#### 4. Test composition sites

**File**: `backend/tests/unit/capture/test_send_message_command.py`, `backend/tests/integration/support/in_memory_capture.py`

**Intent**: Tests pin their own threshold rather than reading `Settings`, so tuning the deployed value can never turn the suite red.

**Contract**: Both construction sites pass an explicit `MatchCriteria`.

#### 5. Settings coverage

**File**: `backend/tests/unit/test_settings.py`

**Intent**: Prove the knob actually reads from the environment, matching the existing `database_url` cases.

**Contract**: A case asserting the default of `0.85` when the variable is absent, and a case asserting an override is read from `VOCABULARY_MATCH_THRESHOLD`.

#### 6. Resolver and command coverage

**File**: `backend/tests/unit/capture/test_vocabulary_resolver.py` (new), `backend/tests/unit/capture/test_send_message_command.py`

**Intent**: The behavioral heart of the slice.

**Contract**: Cases for reuse on a match (same id returned, store size unchanged), mint on a miss (new id, store grows), the `reused` flag's value in both directions for topics and tags, reuse of a tag minted earlier *in the same draft stream*, and the resulting `reused` field on the emitted `DraftTopicEvent`/`DraftTagEvent`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit -v` green
- `cd backend && uv run pytest` green
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean

#### Manual Verification:
- `cd backend && DATABASE_URL=postgresql+asyncpg://weles:weles@postgres:5432/weles uv run fastapi dev src/main.py` starts without error, confirming the new module-level `Settings()` call in `compose.py` does not break boot
- `cd backend && VOCABULARY_MATCH_THRESHOLD=5 uv run python -c "import adapters.compose"` fails loudly rather than starting with a broken threshold

---

## Phase 7: HTTP integration and acceptance scenarios (AC-10, AC-11)

### Overview

Proves the slice over the wire and writes the Gherkin scenarios for the two acceptance criteria S-05 owns. The scenarios are the tests, written here rather than generated by a separate pass, following the S-04 precedent.

### Changes Required:

#### 1. SSE integration coverage

**File**: `backend/tests/integration/test_capture_http.py`

**Intent**: The event contract is what the TUI consumes; assert the new field survives serialization.

**Contract**: The existing draft-stream case additionally asserts `reused` is present and `False` on the first session's `draft_topic`/`draft_tag` frames; a second case drives a second session through the same conversation and asserts `reused` is `True`.

#### 2. Acceptance scenarios

**File**: `backend/tests/features/capture-flow/US-05-vocabulary-reuse.feature`, `backend/tests/bdd/steps/vocabulary_reuse.py` (both new), `backend/tests/bdd/test_features.py`, `backend/pyproject.toml`

**Intent**: AC-10 and AC-11 are this slice's contract with the effort.

**Contract**: Two `@capture-flow`-tagged scenarios, `@AC-10` and `@AC-11`, driven through `capture_client` against `InMemoryCaptureComposition`. AC-10 runs two capture sessions with the same conversation and asserts the second draft's topic and tags carry the ids already stored rather than new ones. AC-11 asserts a first-ever tag is reported to the client as newly minted. Both rely on the repaired deterministic adapter mapping identical labels to identical embeddings, so a same-label pair scores exactly `1.0`. `bdd.steps.vocabulary_reuse` is registered in `pytest_plugins`; `AC-10` and `AC-11` markers are added to `[tool.pytest.ini_options]`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-10 or AC-11)" -v` green
- `cd backend && uv run pytest tests/bdd -m "capture-flow" -v` green (S-01/S-02/S-04 scenarios unaffected)
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run pytest tests/bdd --collect-only` lists the two new scenarios, confirming the step module is registered and no step is unmatched

---

## Phase 8: TUI reused-tag surfacing — stubs

### Overview

Widens the TUI's stream types and draft state to carry the flag. The build is expected to be red until Phase 9.

### Changes Required:

#### 1. Stream event types

**File**: `tui/src/api/stream.ts`

**Intent**: Mirror the backend contract at the client's parse boundary.

**Contract**: `DraftTopicEvent` and `DraftTagEvent` each gain `reused: boolean`; the corresponding `RawReplyStreamEvent` members gain the same field. `parseStreamEvent`'s two branches are left for the next phase.

#### 2. Draft state shape

**File**: `tui/src/store/chat.ts`

**Intent**: A tag is now a label plus its provenance, so the state has to hold both.

**Contract**: The draft's `tags` becomes an array of `{ label: string; reused: boolean }`. Reducer bodies are left for the next phase.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm lint` clean

---

## Phase 9: TUI reused-tag surfacing — behavior

### Overview

Parses the flag, preserves it across the `draft_done` overwrite, and renders newly minted tags distinctly — the half of AC-11 that is actually user-visible.

### Changes Required:

#### 1. Stream parsing

**File**: `tui/src/api/stream.ts`

**Intent**: Carry the field through the raw-to-typed hop.

**Contract**: The `draft_topic` and `draft_tag` branches of `parseStreamEvent` propagate `reused`.

#### 2. Draft reducers

**File**: `tui/src/store/chat.ts`

**Intent**: `draft_done` replaces `tags` wholesale with plain labels, which would erase every flag collected during the stream. The store has to merge rather than overwrite.

**Contract**: `draft_tag` appends `{ label, reused }`. `draft_done` maps each label in its payload to the flag already recorded for that label during the stream, defaulting to `reused: true` for a label never seen streaming — the conservative direction, since claiming something is new when it might not be is the misleading failure.

#### 3. Draft rendering

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: AC-11 requires the user to be *shown* when a new tag is minted; identical rendering for both cases satisfies it only on paper.

**Contract**: `DraftTags` takes the richer tag array and marks newly minted tags distinctly from reused ones.

#### 4. TUI coverage

**File**: `tui/test/stream.test.ts`, `tui/test/chat.test.ts`

**Intent**: Lock the parse, the merge, and the rendering.

**Contract**: Cases for parsing `reused` on both draft frames, for a flag surviving a subsequent `draft_done`, and for a label appearing only in `draft_done` defaulting to reused. Existing fixtures at `tui/test/stream.test.ts:128-143` and `tui/test/chat.test.ts:232-236` gain the new field.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` green
- `cd tui && pnpm typecheck` clean
- `cd tui && pnpm lint` clean

#### Manual Verification:
- Start the backend, run `cd tui && pnpm build && pnpm start`, hold a capture conversation to a draft, then repeat the same conversation in a second session — the second draft's tags render as reused where the first rendered them as new

---

## Testing Strategy

### Unit Tests:
`SimilarityScore` range validation; `Embedding.cosine_similarity` for identical, orthogonal and opposed vectors, for dimension mismatch, for zero magnitude, and for components large enough to overflow a naive magnitude; `MatchCriteria.best_match` for empty candidates, all-below-threshold, a clear winner, and a score tie resolved by `created_at`; `VocabularyResolver` reuse and mint paths including within-stream reuse; `Settings` default and environment override.

### Integration Tests:
Port contract suites for `candidates()` parametrized over adapters, the `EmbeddingPort` contract extended with a finiteness case, `UnitOfWork` rollback observed through `candidates()`, and the SSE stream asserting `reused` across two sessions.

### Manual Testing Steps:
Boot the backend to confirm the new `Settings()` call in the composition root, drive two identical capture sessions through the TUI, and confirm the second marks its tags reused.

## Performance Considerations

`candidates()` returns the entire vocabulary and the domain scores all of it, so each resolution is O(n) in stored rows with n embeddings crossing the port. For a single-user tool with an in-memory store this is irrelevant, and it buys the metric living in exactly one testable place. It does not survive a real store: a SQL/pgvector adapter will want `ORDER BY embedding <=> $1 LIMIT k` pushed down, which means either the port grows a retrieval hint or `MatchCriteria` moves to scoring a pre-narrowed shortlist. That is a deliberate deferral, recorded here so the future adapter's author knows it is expected rather than an oversight.

## Migration Notes

`compose.py` becomes the first module in `src/` to instantiate `Settings()`. Because it is imported by `src/adapters/http/capture.py:8` and by `backend/tests/integration/support/in_memory_capture.py:5`, importing either now requires `DATABASE_URL` to be set. The devcontainer supplies it through the process environment and the repository's root `.env.example` documents it, so no local setup changes; a CI job that imports the app without that variable would need it added.

`DeterministicEmbeddingAdapter`'s output changes shape and dimension. Nothing persists embeddings across runs today — the only store is in-memory — so there is no stored data to migrate. All three existing cases in its contract suite continue to hold.

## References

- `context/changes/capture-flow-tag-dedup/research.md` — required domain-model changes for S-05
- `context/adrs/capture-flow-domain-shape/decision.md:50` — reconciliation lives outside the domain model; port searches, application service reconciles
- `context/efforts/capture-flow/prd.md:69` — FR-009/FR-010 and the open question on what counts as a close match, owned by `/plan`
- `context/efforts/capture-flow/stories.md:55-56` — AC-10, AC-11
- `context/efforts/capture-flow/roadmap.md:64-71` — S-05 slice definition
- `context/archive/changes/2026-08-31-capture-flow-draft-note/plan.md:203,502,504` — S-04's explicit deferral of reconciliation and the seam it named
- `context/foundation/rules/layering.md` — dependency direction and InMemoryFirst
- `context/foundation/rules/contract-testing.md` — one contract suite per port, parametrized over adapters
- `context/foundation/rules/exceptions.md` — `CoreException` codes and the exhaustiveness test
- `context/foundation/test-stack.md` — runners and acceptance-suite commands
