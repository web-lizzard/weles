# Property test — phases 2, 4, 8

ran at 309a9b4

| Field | Value |
| --- | --- |
| change-id | distill-flow-grounded-generation |
| scope | phases 2, 4, 8 |
| engine | Hypothesis (pytest) per `context/foundation/test-stack.md` |
| numRuns | 100 per property (200 on aggressive follow-up pass) |
| interruptAfterTimeLimit | 30s (60s aggressive pass) |
| date | 2026-09-05 |

## Oracle-able surface

| File | Phase |
| --- | --- |
| `backend/src/domain/distill/value_objects.py` | 2 |
| `backend/src/domain/distill/card.py` | 4 |
| `backend/src/domain/distill/card_factory.py` | 4 |
| `backend/src/adapters/out/in_memory/distill/note_document_parser.py` | 8 |

## Properties hunted

### Phase 2 — value objects

1. **Strip idempotence** — constructing `CardSide` / `Anchor` from an already-canonical value is a fixed point.
2. **Breach iff within bounds** — `CardLengthPolicy.breach` returns `None` exactly when both sides fit their respective maxima.
3. **Front-first breach ordering** — when both sides exceed, the detail names the front bound.

### Phase 4 — aggregate and factory

1. **Identical sides iff casefold-equal** — `IdenticalCardSidesError` is raised exactly when `front.value.casefold() == back.value.casefold()` for valid sides.
2. **Unresolved always ungrounded** — `AnchorResolution.UNRESOLVED` mints `Discard(ungrounded)` regardless of length policy breach.
3. **Resolved live iff no breach** — `AnchorResolution.RESOLVED` yields `discard is None` exactly when `length_policy.breach` is `None`.

### Phase 8 — parser

1. **Normalization idempotence** — `_normalize(_normalize(t)) == _normalize(t)`.
2. **Empty quote never resolves** — `""`, whitespace-only, and newline/tab-only quotes always return `False`.
3. **Resolves implies single-block substring** — `True` only when the normalized quote is a substring of some single normalized block.
4. **Cross-block quotes do not resolve** — quotes spanning two blocks (when not wholly contained in either block) return `False`.

### Aggressive follow-up (classified, not triaged)

- Unicode casefold pairs (Turkish İ/i, German ß/ss, Greek Ω/ω).
- List-marker stripping (`#`, `>`, `-`, `+`, `1.`, `2)`).
- Emphasis wrapper symmetry (`**`, `_`, `` ` ``, `*`).
- Multi-line whitespace-only block separators.
- Exotic whitespace in `CardSide` strip (NBSP, em-space, tab).

## Specimens

**no new edge found**

## Classified (not triaged)

All aggressive follow-up properties held across their budgets; no illegal-input or too-strong residue to record.

## Retractions

*(none)*
