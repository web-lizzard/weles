# Mutation test review r3

ran at 05d1155

- **change-id**: remember-flow-due-count
- **scope**: phase 2
- **mutate surface**: `backend/src/domain/remember/due_partition.py`
- **engine**: mutmut 3
- **run notes**: Full-suite green-verify was waived on user request (2× US-07 BDD scenarios red on stub `DueCountQuery`). Mutmut could not collect stats until pytest excluded `tests/bdd`; run was scoped with `only_mutate = ["src/domain/remember/due_partition.py"]` for this session only (not committed).

## Mutate surface

- `backend/src/domain/remember/due_partition.py`

## Specimens

None.

**no new edge found**

Engine report (`mutants/mutmut-cicd-stats.json`): 64 total, 64 killed, 0 survived.

## Classified (not triaged)

None.
