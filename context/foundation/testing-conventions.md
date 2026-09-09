# Testing Conventions

How tests are written in this repository, and what each quality lane runs on.
Backend (`backend/`, Python) is the default surface; the TUI (`tui/`, Node) is
named explicitly wherever it differs.

## Conventions

### Test layout

| Kind | Location |
| --- | --- |
| Backend unit | `backend/tests/unit/<context>/` — `capture/`, `distill/`, `shared/` |
| Backend port contracts | `backend/tests/unit/<context>/contracts/test_<port>_contract.py` |
| Backend property | `backend/tests/property/<context>/` |
| Backend integration | `backend/tests/integration/` |
| Backend acceptance | features `backend/tests/features/<effort-id>/US-nn-<slug>.feature`, steps `backend/tests/bdd/steps/<subject>.py` |
| TUI | `tui/test/<subject>.test.ts` — `.test.tsx` when the subject renders Ink |

Backend test packages carry `__init__.py`.

### Import style

Backend tests import production code by its `src`-rooted absolute path —
`from domain.distill.note_document import NoteDocument`,
`from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository`.
This works because `pyproject.toml` sets `pythonpath = ["src", "tests"]`; never
add `sys.path` juggling or a relative `..` import. Test-support modules import
the same way (`from integration.support.in_memory_distill import ...`), carrying
the `# pyright: ignore[reportImplicitRelativeImport]` the tree already uses.

TUI tests import production code by relative path from `test/` into `src/`
(`import { listNotes } from "../src/api/notes"`), types with `import type`.

### `describe` / `it` nesting

Backend: flat module-level `def test_…` / `async def test_…` functions. No test
classes, no nesting. The module path plus the test name carries the grouping.

TUI: exactly one top-level `describe("<subject under test>")` per file, with
flat `it(...)` cases inside it. No nested `describe`.

### Mock-helper location

- Compositions reused across suites: `backend/tests/integration/support/`
  (`in_memory_capture.py`, `in_memory_distill.py`), also imported by the BDD
  conftest.
- A double used by one module: a module-private `class _Name` in that test file.
- Shared acceptance fixtures: `backend/tests/bdd/conftest.py`. Step modules are
  append-only and registered in `pytest_plugins` in
  `backend/tests/bdd/test_features.py`.
- TUI: `vi.mock("../src/api/<module>", …)` at the top of the file that needs it;
  no shared mock directory.

`backend/tests/unit/conftest.py` holds cross-cutting fixtures only. Unit tests
otherwise declare no `@pytest.fixture` — they build what they need in the test
body.

### Single-file invocation

```bash
cd backend && uv run pytest tests/unit/distill/test_note_document.py -v
cd tui && pnpm vitest run test/notesStore.test.ts
```

### Test-double policy

Prefer the real in-memory adapter over a hand-written double. Every port has one
behavioural contract suite parametrized over its implementations
(`_IMPLEMENTATIONS: list[Callable[[], Port]]`, `ids=["in_memory"]`); the
in-memory implementation runs it on every invocation, and costly LLM-backed
adapters run the same suite on a non-blocking cadence — see
`context/foundation/rules/contract-testing.md`.

Hand-rolled `_Fake…` classes are for driving a collaborator into a state or an
error the real adapter cannot reach on demand. Never patch or monkeypatch
production internals.

TUI doubles the API module boundary only (`vi.mock` over `src/api/*`). Stores,
screens, and components are exercised for real, rendered through
`ink-testing-library`.

### Determinism

Backend tests call `datetime.now(UTC)` and `uuid4()` directly and assert on
structure and relations, never on a wall-clock value. There is no injected clock
and no frozen time; a test that would need one is a test asserting the wrong
thing.

TUI tests that involve timers freeze them: `vi.useFakeTimers()` in `beforeEach`,
`vi.useRealTimers()` in `afterEach`, advancing with
`await vi.advanceTimersByTimeAsync(ms)`. Ids and timestamps in fixtures are
fixed literals (`"00000000-0000-4000-8000-000000000001"`).

### Test-data shape

Backend: a module-private factory with defaults —
`def _sample_card(note_id: NoteId, discard: Discard | None = None) -> Card:` —
overridden per test by keyword. No builder classes, no shared factory package.

TUI: module-level `const` literals typed by the production API type
(`const NOTE: NoteListItem = {…}`, `const CARDS: Card[] = [ … ]`).

### How many tests a phase produces

Backend: 2–6 tests per phase. TUI: 1–5. One behaviour per test. A phase that
wants more is a phase that should have been split.

### How a test is named

A full sentence stating the observable behaviour, including the condition that
provokes it:

```
test_locate_returns_exact_span_equal_to_a_plain_paragraph_quote
test_locate_degrades_a_heading_match_and_reports_the_second_block
it("fetches immediately on startPolling, then once per interval tick")
```

The name states what the caller observes. It does not name the method under
test alone, does not say "works", "correctly", "should", or "handles", and does
not restate the implementation.

### Private members

Tests exercise the public surface only. A test never reads or calls an
underscore-prefixed attribute of production code; a behaviour reachable no other
way is a design signal, not a licence. Underscore names inside a test module's
own fakes and factories are unaffected.

## Stack

### Unit

- **Runner**: pytest 8 with pytest-asyncio (`asyncio_mode = "auto"`; async tests
  need no marker). TUI: vitest 3, `environment: "node"`.
- **Run target**: `cd backend && uv run pytest tests/unit` — full backend suite
  is `cd backend && uv run pytest`. TUI: `cd tui && pnpm test`.
- **Single file**: `cd backend && uv run pytest <file> -v`;
  `cd tui && pnpm vitest run <file>`.
- **Tests live in**: `backend/tests/unit/`, `tui/test/`.
- **Blocking**: blocking. A phase does not close while the unit suite is red.

### BDD

- **Runner**: pytest-bdd 8 on top of pytest. `bdd_features_base_dir = "tests/features"`.
- **Run target**: `cd backend && uv run pytest tests/bdd -v`. Filter by Gherkin
  tag, which pytest-bdd exposes as a marker:
  `cd backend && uv run pytest tests/bdd -m "distill-flow and AC-03" -v`.
  Every new tag is registered in `[tool.pytest.ini_options] markers`.
- **Tests live in**: features `backend/tests/features/<effort-id>/`, steps
  `backend/tests/bdd/steps/`, loader `backend/tests/bdd/test_features.py`.
- **JSON formatter**: `--cucumberjson=<path>`.
- **Step statuses in that JSON**: `passed`, `failed`, `skipped`, `undefined`.
- **Dry run**: `--collect-only` collects without executing. Its exit code
  carries no information about step definedness — read the report, not the
  status. pytest-bdd has no cucumber-js-style dry run; an unmatched Gherkin line
  surfaces as a collection or runtime failure naming that line.
- **Blocking**: blocking. Scenarios are expected red between `/bdd` and
  `/implement`; a phase closes only once its own scenarios are green.
- **TUI**: no node-side BDD tooling installed. The lane resolves to the backend.

### Mutation

- **Engine**: mutmut 3, configured in `[tool.mutmut]` —
  `source_paths = ["src"]`, `pytest_add_cli_args_test_selection = ["tests/"]`.
- **Green-verify**: `cd backend && uv run pytest`.
- **Invoke**: `cd backend && uv run mutmut run`.
- **Report**: `backend/mutants/mutmut-cicd-stats.json`, JSON. Survivors are also
  readable with `uv run mutmut results` and `uv run mutmut show <mutant>`;
  `backend/mutants/` is gitignored.
- **Production surface**: `backend/src/`.
- **Tests live in**: the lane writes no committed tests of its own. A surviving
  mutant becomes a triage row, and the test that kills it is written into
  `backend/tests/unit/` under the unit conventions above.
- **Blocking**: advisory. A surviving mutant never blocks a phase.
- **TUI**: no node-side mutation engine installed. The lane resolves to the
  backend.

### Property

- **Engine**: Hypothesis 6 inside pytest.
- **Green-verify**: `cd backend && uv run pytest`.
- **Invoke**: `cd backend && uv run pytest tests/property -k <pattern> -v`.
- **Host runner**: `@given(...)` with Hypothesis strategies on a plain pytest
  test function — the unit conventions above apply unchanged.
- **Time budget**: 30 seconds per hunt.
- **Property file**: written under `backend/tests/property/<context>/`.
  Session-local throwaway properties are not committed; a shrunk counterexample
  is committed as a pinned regression test.
- **Blocking**: advisory. A counterexample becomes a triage row, not a gate.
- **TUI**: no node-side property engine installed. The lane resolves to the
  backend.
