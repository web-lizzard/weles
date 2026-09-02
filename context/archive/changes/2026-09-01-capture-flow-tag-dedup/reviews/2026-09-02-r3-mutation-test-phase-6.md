# Mutation test review r3 — phase 6

ran at 7a6717b

- **change-id**: capture-flow-tag-dedup
- **scope**: phase 6
- **mutate surface**:
  - `backend/src/application/capture/services/vocabulary.py`
  - `backend/src/application/capture/commands/send_message.py`
  - `backend/src/adapters/compose.py`
- **engine**: mutmut 3.7 + pytest (`context/foundation/test-stack.md`)
- **date**: 2026-09-02

## Specimens

### R3-F1 — WARNING

- **Operator**: ArgumentReplacement
- **Location**: `src/application/capture/commands/send_message.py:122`
- **Tests still passed**: Survived
- **Mutant**: `reused=tag_resolution.reused` → `reused=None` (`handle__mutmut_63`); sibling `handle__mutmut_65` drops the `reused` keyword entirely — same missing oracle
- **Fix**: A drafting-turn command test must assert each emitted `DraftTagEvent.reused` matches the resolver (`False` on first mint in a stream, `True` when the tag row already exists); structural pydantic failures on `DraftTopicEvent` are already killed, but tag-frame forwarding is not oracle-tested.

## Classified (not triaged)

- **`VocabularyResolver` reuse-or-mint** (`vocabulary.py`) — all mutants killed; aligns with property-test r2 and unit coverage.
- **`compose.py` factory helpers** — 35 mutants with status `no tests`; composition-root glue outside pytest selection.
- **`GenerateReplyCommand.__init__` assignment-to-`None`** — survived; dependency-injection wiring not asserted and outside phase-6 contract.
- **Pre-S05 `handle` paths** (topic extraction, reply text accumulation, `ReplyDoneEvent` assembly) — survived; not introduced in phase 6.
- **`saw_draft` flag assignments** on topic/tag branches — survived under mutmut's per-mutant test selection without hitting draft persistence assertions; classified as unproductive for this phase-scoped run.
- **Destructive tag-resolution mutants** (`resolve_tag` call removed, arguments nulled) — survived only because selected tests do not execute the draft-tag yield path with behavioral assertions.

## Summary

**1 specimen queued** (WARNING). Resolver behavior is well-mutated; the command layer still lacks an oracle that `DraftTagEvent.reused` is forwarded from `VocabularyResolver`, which plan phase 6.5 explicitly called for.
