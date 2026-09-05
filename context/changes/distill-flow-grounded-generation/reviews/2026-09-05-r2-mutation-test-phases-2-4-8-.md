# Mutation test — phases 2, 4, 8

ran at 309a9b4

| Field | Value |
| --- | --- |
| change-id | distill-flow-grounded-generation |
| scope | phases 2, 4, 8 |
| engine | mutmut 3.7.0 + pytest (`context/foundation/test-stack.md`) |
| date | 2026-09-05 |

## Mutate surface

| File | Phase |
| --- | --- |
| `backend/src/domain/distill/value_objects.py` | 2 |
| `backend/src/adapters/http/errors.py` | 2 |
| `backend/src/domain/distill/card.py` | 4 |
| `backend/src/domain/distill/card_factory.py` | 4 |
| `backend/src/adapters/out/in_memory/distill/note_document_parser.py` | 8 |

88 mutants exercised; 4 survived; 84 killed.

## Specimens

### R2-F1 — leading block markers must strip to empty

- **Severity**: WARNING
- **Operator**: `argument_replacement`
- **Location**: `backend/src/adapters/out/in_memory/distill/note_document_parser.py:26`
- **Tests still passed**: Survived
- **Mutant**: `_LEADING_MARKER_PATTERN.sub("", text.strip())` → `_LEADING_MARKER_PATTERN.sub("XXXX", text.strip())`
- **Fix:** assert `_normalize("# TCP Handshake") == "TCP Handshake"` (or an equivalent contract case that a heading quote resolves only when the `#` prefix is removed, not replaced)

### R2-F2 — whitespace runs must collapse to a single space

- **Severity**: WARNING
- **Operator**: `argument_replacement`
- **Location**: `backend/src/adapters/out/in_memory/distill/note_document_parser.py:29`
- **Tests still passed**: Survived
- **Mutant**: `_WHITESPACE_PATTERN.sub(" ", text)` → `_WHITESPACE_PATTERN.sub("XX XX", text)`
- **Fix:** assert `_normalize("Connections are\nestablished") == "Connections are established"` (or a contract case that reflowed quotes still resolve after single-space collapse)

### R2-F3 — mint must stamp created_at in UTC

- **Severity**: WARNING
- **Operator**: `argument_replacement`
- **Location**: `backend/src/domain/distill/card_factory.py:36`
- **Tests still passed**: Survived
- **Mutant**: `created_at=datetime.now(UTC)` → `created_at=datetime.now(None)`
- **Fix:** assert every minted `Card.created_at.tzinfo is UTC`, including live cards

### R2-F4 — oversized discard must stamp discarded_at in UTC

- **Severity**: WARNING
- **Operator**: `argument_replacement`
- **Location**: `backend/src/domain/distill/card_factory.py:58`
- **Tests still passed**: Survived
- **Mutant**: `discarded_at=datetime.now(UTC)` → `discarded_at=datetime.now(None)` on the oversized `Discard` branch
- **Fix:** assert an oversized mint sets `card.discard.discarded_at.tzinfo is UTC` (the ungrounded branch already asserts UTC; the oversized path does not)

## Classified (not triaged)

| Operator | Location | Why classified |
| --- | --- | --- |
| *(all other mutants)* | `value_objects.py`, `card.py`, `errors.py` | Killed — aligns with unit, contract, and property-test r1 coverage on phases 2, 4, 8 |
