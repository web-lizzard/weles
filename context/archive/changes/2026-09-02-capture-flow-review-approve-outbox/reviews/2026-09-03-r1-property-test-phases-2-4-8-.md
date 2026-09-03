# Property test — phases 2, 4, 8

ran at 1266137

| Field | Value |
| --- | --- |
| change-id | capture-flow-review-approve-outbox |
| scope | phases 2, 4, 8 |
| engine | Hypothesis 6.165.10 inside pytest (`context/foundation/test-stack.md`) |
| max_examples | 100 per property |
| deadline | 5000 ms per property |
| date | 2026-09-03 |

## Oracle-able surface

Listed phases were scanned per plan `Changes Required` and phase SHAs. Pure domain under `backend/src/domain/` survives the filter; adapters, application commands, and HTTP wiring are dropped.

| File | Phase |
| --- | --- |
| `backend/src/domain/shared/outbox/model.py` | 2 |
| `backend/src/domain/capture/outbox.py` | 2 |

Phase 4 contributes only in-memory adapter paths (`appender.py`, `store.py`, `claimer.py`) — no oracle-able domain file. Phase 8 contributes only application command paths (`send_message.py`, `approve_note.py`) — no oracle-able domain file. Both phases were dropped from the union; the hunt ran on the phase-2 domain surface above.

## Properties hunted

Input-space / boundary checks with independent reference oracles (not SUT reimplementation):

1. **Envelope lifecycle equivalence** — random sequences of `claim` / `consume` / `fail` match a reference state machine; illegal ops are atomic.
2. **Retry cut-off** — after `claim`, `fail(max_attempts)` clears claim fields iff `attempts < max_attempts`, otherwise settles `FAILED`.
3. **Terminal immutability** — `CONSUMED` and `FAILED` envelopes reject further mutations.
4. **Claim accounting** — each successful `claim` from `PENDING` increments `attempts` by exactly one; `consume` leaves `attempts` unchanged.
5. **Envelope type identity** — `pending()` preserves the supplied `EnvelopeType` name and version.
6. **Payload denormalization** — `NoteApprovedPayload.of(...).to_envelope()` carries canonical topic/tag labels and note content in the envelope payload (compared against `Label`/`NoteContent` canonical values, not raw generator strings).

## Specimens

**no new edge found**

## Classified (not triaged)

| Property | Why classified |
| --- | --- |
| Envelope payload labels match raw generator strings | Oracle compared unstripped input; `Label` and `NoteContent` canonicalize via `.strip()` in `value_objects.py`. Inputs like `'0\r'` or `'\r'` are either normalized before snapshot or rejected as empty — not a missing edge in `NoteApprovedPayload`. |
| Fixed-count `claim`/`fail` cycles without respecting terminal status | With `max_attempts=1`, the first cycle dead-letters the envelope; a second `claim` correctly raises `EnvelopeNotPendingError`. Property too strong for the state machine, not an SUT defect. |

## Retractions

(none)
