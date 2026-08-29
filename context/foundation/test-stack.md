# Test Stack

How tests are organized in this repository and which runners to invoke.

## Unit and integration (pytest)

- **Runner**: pytest + pytest-asyncio
- **Location**: `backend/tests/unit/`, `backend/tests/integration/`
- **Invoke**: `cd backend && uv run pytest`
- **Filter**: `uv run pytest tests/unit/test_settings.py -v`

Async tests use `@pytest.mark.asyncio`; `asyncio_mode = "auto"` is set in `pyproject.toml`.

## Acceptance / BDD (pytest-bdd)

- **Runner**: [pytest-bdd](https://pytest-bdd.readthedocs.io/) 8.x (Gherkin on top of pytest)
- **Feature files**: `backend/tests/features/<effort-id>/US-nn-<slug>.feature`
- **Step definitions**: `backend/tests/bdd/steps/<subject>.py` (append-only; import new modules from `tests/bdd/test_features.py`)
- **Scenario loader**: `backend/tests/bdd/test_features.py`

### Commands

| Goal | Command |
| --- | --- |
| Full acceptance suite | `cd backend && uv run pytest tests/bdd -v` |
| Filter by effort + criterion | `cd backend && uv run pytest tests/bdd -m "capture-flow and AC-01" -v` |
| Collect only (no execution) | `cd backend && uv run pytest tests/bdd --collect-only` |

Gherkin tags become pytest markers. Use the tag text in `-m` expressions (`capture-flow`, `AC-01`, combined with `and` / `or`).

### Undefined steps

pytest-bdd has no cucumber-js-style dry run. Missing step definitions surface as collection or runtime failures naming the unmatched Gherkin line. Run the acceptance suite to discover gaps.

### Coexistence

Unit/integration and acceptance suites share pytest but live in separate directories. `uv run pytest` without a path runs everything; acceptance scenarios are expected to stay red until `/implement` turns assertions green.

## Mutation testing (mutmut)

- **Engine**: [mutmut](https://mutmut.readthedocs.io/) + pytest
- **Production surface**: `backend/src/`
- **Config**: `[tool.mutmut]` in `backend/pyproject.toml`

### Commands

| Goal | Command |
| --- | --- |
| Full campaign | `cd backend && uv run mutmut run` |
| List survivors | `cd backend && uv run mutmut results` |
| Show mutant diff | `cd backend && uv run mutmut show <mutant_name>` |

Artifacts land in `backend/mutants/` (gitignored). Used by `/mutation-test` on backend changes.

## Property-based testing (Hypothesis)

- **Engine**: [Hypothesis](https://hypothesis.readthedocs.io/) inside pytest
- **Location**: property tests live in `backend/tests/` alongside unit tests

### Commands

| Goal | Command |
| --- | --- |
| Run all tests (incl. properties) | `cd backend && uv run pytest` |
| Filter by name | `cd backend && uv run pytest -k <pattern> -v` |

Used by `/property-test` on backend changes. Session-local throwaway properties during a hunt are not committed.

