# Topic and Tag Deduplication Through Reuse — Plan Brief

> Full plan: `plan.md`

## What & Why

Every drafted note currently mints a fresh `Topic` and a fresh `Tag` per proposed label, so capturing the same subject twice produces semantically identical duplicate vocabulary rows. This slice makes drafting check the existing vocabulary first, reuse a close match, and show the user which tags were newly minted. It realizes AC-10 and AC-11 of the `capture-flow` effort.

## Starting Point

`VocabularyResolver` embeds a label, mints, and adds — unconditionally, with no lookup step. The repository ports expose only `add`/`get`-by-id, so nothing can ask a store what it already holds. No dedup coverage exists anywhere in the repo.

## Desired End State

A second capture session about an already-captured subject attaches the *existing* topic and tag rows to its note — same ids, same labels — instead of near-duplicates, and the TUI marks reused tags distinctly from newly minted ones. The matching rule is a domain value object assertable with no repository or adapter in sight, and its threshold is an environment variable rather than a committed constant.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where the matching rule lives | Criteria (metric + threshold) in the domain; reuse-or-mint orchestration stays in the application service | Makes "what counts as close" a named, testable domain object without contradicting the ADR's placement of reconciliation outside the domain | Plan |
| What the port returns | A plain list of stored rows with their embeddings — no scoring | The domain gets a genuine choice rather than inheriting the adapter's ranking, and the adapter stays a dumb data-access layer | Plan |
| Who computes similarity | The domain, via `Embedding.cosine_similarity` | Keeps the metric in exactly one place so it cannot drift between adapters | Plan |
| What "close match" means | Cosine similarity above a threshold; no exact-label path | Matches the PRD's intent of catching semantic near-duplicates rather than typographic ones | Frame (`prd.md:69` left it to `/plan`) |
| Selection among qualifying candidates | Highest score; ties broken by the older `created_at` | Total and deterministic, so the same store always yields the same answer and one assertion pins it | Plan |
| Where the threshold is configured | `Settings.vocabulary_match_threshold`, default `0.85`, env `VOCABULARY_MATCH_THRESHOLD` | Tuning it costs an environment variable rather than a commit | Plan |
| How AC-11 becomes visible | `reused: bool` on `DraftTopicEvent`/`DraftTagEvent`, surfaced in the TUI | "The user is shown the new tag" is unmet if new and reused render identically | Plan |
| Test embeddings | Vectors constructed directly in tests; `DeterministicEmbeddingAdapter` repaired, not replaced | Lets tests sit precisely above and below the threshold, where the rule can actually break | Plan |
| ADR relationship | `kinds: [implements]` — no amendment | Reconciliation itself stays in the application service, so `capture-flow-domain-shape` remains accurate | Plan |

## Scope

**In scope:** `SimilarityScore`, `MatchCriteria` and `Embedding.cosine_similarity` in the domain; `candidates()` on both vocabulary ports and their in-memory adapters; repairing `DeterministicEmbeddingAdapter`'s numerics; rewriting `VocabularyResolver` to reuse-or-mint; the `reused` flag through the SSE contract into the TUI; the threshold setting and its wiring; AC-10/AC-11 acceptance scenarios.

**Out of scope:** any change to the `Topic`, `Tag`, `Note`, `Message` or `CaptureSession` aggregates; `CaptureSession.topic`, which the ADR excludes from reuse by design; `DraftDoneEvent`'s shape (breaking, and its consumer surface is S-06); a semantically meaningful embedding provider; exact-label or case-insensitive matching; lazy reconstruction of `Topic`/`Tag` from stored ids; amending the domain-shape ADR.

## Architecture / Approach

```
GenerateReplyCommand
        │  label
        ▼
VocabularyResolver ──embed()──▶ EmbeddingPort
  (application)     ──candidates()──▶ Topic/TagRepository   ← retrieval only
        │                                    (adapter: dumb data access)
        │  target embedding + candidates
        ▼
MatchCriteria.best_match()  ← the rule (domain): cosine, threshold, tie-break
        │
        ├─ VocabularyMatch  → reuse existing entry, reused=True   (no mint, no add)
        └─ None             → mint + add,          reused=False
```

The port retrieves, the domain decides what is close enough, the application service decides what to do about it. The threshold enters as a `Settings` value converted to a `SimilarityScore` once in `compose.py`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Domain matching — stubs | `SimilarityScore`, `MatchCriteria`, `VocabularyMatch`, metric signature, three exceptions | Generic model over a constrained `TypeVar` must stay a validatable pydantic type |
| 2. Domain matching — behavior | Range validation, overflow-safe clamped cosine, the selection rule, exception mapping | A naive cosine returns `NaN`/`0.0` on real adapter output; missed mapping entries redden the exhaustiveness test |
| 3. Retrieval + conditioning — stubs | `candidates()` on both ports and adapters; widened embedding dimension | — |
| 4. Retrieval + conditioning — behavior | `candidates()` implementations, contract cases, repaired embedding adapter | Changing the adapter's output must keep its three existing contract cases green |
| 5. Reuse-or-mint + config — stubs | `ResolvedTopic`/`ResolvedTag`, resolver signature, `reused` on two DTOs, settings field | — |
| 6. Reuse-or-mint + config — behavior | The reuse-or-mint rewrite, stream wiring, composition root, settings coverage | `compose.py` becomes the first production `Settings()` consumer, so importing it starts requiring `DATABASE_URL` |
| 7. HTTP + acceptance (AC-10, AC-11) | SSE integration cases, `US-05` feature and steps, markers, plugin registration | An unregistered step module silently loads no scenarios |
| 8. TUI — stubs | Widened stream types and draft-state shape | Build is deliberately red until Phase 9 |
| 9. TUI — behavior | Flag parsed, preserved across `draft_done`, rendered distinctly | `draft_done` overwrites `tags` wholesale and would erase every flag unless the store merges |

**Prerequisites:** S-04 (`capture-flow-draft-note`), archived and green.
**Estimated effort:** 9 phases; the domain pair and the application pair carry most of the weight, the two stubs-only adapter and TUI phases are thin.

## Open Risks & Assumptions

- **The `0.85` default is a starting guess, not a measured value.** It is grounded only against the deterministic stub, where unrelated labels measured a maximum cosine of `0.6459` over 19,900 pairs at 32 dimensions. A real embedding model will need it re-tuned — which is exactly why it is a setting.
- **Hash embeddings carry no semantics, so `"python"` and `"Python"` will not merge** (measured cosine `0.127`). Dedup is genuinely exercised only for identical labels until a real embedding provider lands. The acceptance scenarios are written to that limit.
- **`candidates()` pulls the whole vocabulary across the port on every resolution.** Irrelevant at single-user, in-memory scale; it will not survive a SQL/pgvector adapter without either a retrieval hint on the port or moving `MatchCriteria` to score a pre-narrowed shortlist.
- **Assumption:** nothing persists embeddings between runs today, so changing the adapter's dimension and value range needs no data migration.
- **Assumption:** a label seen only in `draft_done` and never in a streamed `draft_tag` frame is treated as reused, on the grounds that wrongly claiming novelty is the more misleading failure.

## Success Criteria (Summary)

- A second identical capture session attaches the existing topic and tag ids rather than minting duplicates, proven by the `@AC-10` scenario.
- A first-ever tag is reported to the client as newly minted and rendered distinctly in the TUI, proven by the `@AC-11` scenario and the TUI suite.
- The threshold is changeable through `VOCABULARY_MATCH_THRESHOLD` with no code change, and an out-of-range value fails at startup rather than silently disabling reuse.
