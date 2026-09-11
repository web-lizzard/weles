# Mutation test review r4

- **change-id**: remember-flow-card-rejection
- **scope**: phase 6
- **date**: 2026-09-11
- **ran at** daab660

## Mutate surface

- `backend/src/application/distill/commands/discard_card.py`
- `backend/src/adapters/out/worker/handlers/card_discard.py`

## Specimens

### R4-F1

- **Severity**: CRITICAL
- **Operator**: keyword argument → None
- **Location**: `backend/src/application/distill/commands/discard_card.py:33`
- **Tests still passed**: Survived (before killing test)
- **Mutant**: `detail=detail` → `detail=None` on `Discard(...)`
- **Fix**: `Discard.detail` must equal the `handle()` `detail` argument, including a non-None string.
- **Branch**: confirmed kill
- **Evidence**: killing test `test_discard_stamps_a_non_none_detail_onto_the_card` in `backend/tests/unit/distill/test_discard_card_command.py`; mutant `application.distill.commands.discard_card.xǁDiscardCardCommandǁhandle__mutmut_19` killed on re-run. Evidence commit `ac022bc`. Queues no row.

## Classified (not triaged)

Unproductive logging (operator, location, why):

- **handle__mutmut_4** (`card_discard.py:23`, `envelope.id` → `None`): log-line operand
- **handle__mutmut_5** (`card_discard.py:23`, exception message dropped): log-line string
- **handle__mutmut_6** (`card_discard.py:23`, second logger argument removed): log-line operand
- **handle__mutmut_7** (`card_discard.py:23`, `XX…XX` around the message): log-line string
- **handle__mutmut_5** (`discard_card.py:25`, `card_id.value` → `None`): log-line operand
- **handle__mutmut_7** (`discard_card.py:25`, second logger argument removed): log-line operand
- **handle__mutmut_8** (`discard_card.py:25`, `XX…XX` around the message): log-line string
- **handle__mutmut_12** (`discard_card.py:28`, `card_id.value` → `None`): log-line operand
- **handle__mutmut_14** (`discard_card.py:28`, second logger argument removed): log-line operand
- **handle__mutmut_15** (`discard_card.py:28`, `XX…XX` around the message): log-line string
