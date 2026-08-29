# Backend Agentic Rules Implementation Plan

## Overview

Materialize the `hexagonal-arch-shape` ADR's invariants (layering, CQRS-lite, contract testing, exception mapping) as agent-facing rule files that both Claude Code and Cursor load automatically while working under `backend/`, and bootstrap the one piece of code the ADR's amendment names explicitly: `CoreException`, its `code` derivation, and the HTTP adapter's exhaustive code-to-status mapping.

## Current State Analysis

The backend is a bare hexagonal scaffold: `backend/src/{domain,application}/__init__.py` are empty, `backend/src/adapters/{db,notion}/__init__.py` are empty, and the only real code is `backend/src/config/settings.py` and `backend/src/adapters/http/health.py` wired from `backend/src/main.py`. No exception hierarchy exists anywhere in the codebase yet.

Both agent-rule ecosystems already exist with one topic each: `.claude/rules/language-policy.md` (plain markdown, no frontmatter, pulled into context via `@import` in root `CLAUDE.md`) and its Cursor twin `.cursor/rules/language-policy.mdc` (frontmatter `description`/`alwaysApply`). `.cursor/rules/devcontainer-hooks.mdc` additionally demonstrates the `globs` key for path-scoped Cursor rules. Separately, `.claude/skills/*` are already symlinks into `.ordo/skills/*` — this repo's existing precedent for keeping one authored copy and exposing it in multiple places via symlink.

## Desired End State

- Four canonical rule documents under `context/foundation/rules/` (`layering.md`, `cqrs-lite.md`, `contract-testing.md`, `exceptions.md`) each state one slice of the ADR's invariants as directives, and each carries one frontmatter block readable by both ecosystems.
- `.claude/rules/{topic}.md` and `.cursor/rules/{topic}.mdc` are symlinks to those four canonical files — there is exactly one authored copy of each rule's text.
- Editing or reading a file under `backend/**` in Claude Code loads the matching rule(s) automatically (`paths: ["backend/**"]`); the same files activate as path-scoped rules when Cursor is pointed at `backend/**` (`globs: backend/**`).
- `backend/src/domain/exceptions.py` defines `CoreException`, whose subclasses get an auto-derived, overridable, snake_case `code`.
- `backend/src/adapters/http/errors.py` owns the one `code -> HTTP status` mapping table and a FastAPI exception handler wired into `backend/src/main.py`. A test walks `CoreException.__subclasses__()` recursively and fails on any code missing from the mapping table or on any two subclasses colliding on the same code.

### Key Discoveries:
- `context/adrs/hexagonal-arch-shape/decision.md` (plus its "Amendment (2026-08-28)" section) is the sole source of every invariant this change encodes — rule files cite it, they don't restate its rationale.
- `context/foundation/README.md:13-15` — foundation docs are for content that "outlives any one change"; the anti-pattern is change-scoped docs, which these rule files are not.
- Claude Code's `.claude/rules/` supports a `paths:` glob-list frontmatter key for path-scoped loading, and explicitly supports symlinked rule files, including individual-file symlinks (code.claude.com/docs/en/memory, "Organize rules with `.claude/rules/`" / "Share rules across projects with symlinks").
- Cursor `.mdc` frontmatter precedent already in this repo: `.cursor/rules/devcontainer-hooks.mdc:1-4` (`description`/`globs`/`alwaysApply`).
- `backend/pyproject.toml` pins ruff (`E,F,I,UP,B`, line-length 88) and basedpyright over `src`/`tests`, py312 — new modules must satisfy both, matching the style already in `backend/src/config/settings.py` (full type hints, `ClassVar` annotations).
- Test style precedent: flat `tests/unit/`/`tests/integration/`, function-based, fully type-hinted (`backend/tests/unit/test_settings.py`, `backend/tests/integration/test_health.py`).

## What We're NOT Doing

- Not creating `context/foundation/architecture.md` — that is a different, `/plan`-time foundation prior (per `references/questioning.md`), out of scope here.
- Not creating a bounded-context-specific exceptions module (e.g. `domain/notes/exceptions.py`) — no bounded context exists yet.
- Not building an exception catalog — only the mechanism, plus one representative subclass (`NotFoundError`) so the exhaustiveness test is not vacuous.
- Not authoring contract-test suites — the `contract-testing.md` rule documents the requirement, but there are no ports/adapters yet to test against.
- Not touching the TUI or root `CLAUDE.md`.

## Implementation Approach

Rule content is authored once, per topic, at `context/foundation/rules/`, then exposed to each ecosystem purely via symlink — so drift between "what Claude Code enforces" and "what Cursor enforces" is structurally impossible. The `CoreException` bootstrap follows the plan's stubs-then-behavior split: the class/handler shapes land first (import-checkable, no behavior), then the derivation logic and the exhaustiveness test land together as the TDD'd behavior.

## Critical Implementation Details

The frontmatter block combining `paths` (Claude Code) and `description`/`globs`/`alwaysApply` (Cursor) in one file relies on each tool ignoring frontmatter keys it doesn't recognize — both tools document symlink-sharing as a supported pattern, which only works if unknown keys are tolerated. Phase 1's Manual Verification confirms this empirically in both tools rather than leaving it as an unverified assumption. Separately, Claude Code's path-scoped rules only reload when a matching file is *read*, not when a new file is *created* under the pattern (a documented open limitation) — not a blocker here since `backend/**` already contains files the agent routinely reads, but worth knowing if a rule ever seems to not apply to a freshly created file in an empty subtree.

## Phase 1: Agentic rules content and wiring

### Overview

Author the four canonical rule documents and expose them to both Claude Code and Cursor via symlink, path-scoped to `backend/**`.

### Changes Required:

#### 1. Canonical rule documents

**File**: `context/foundation/rules/layering.md`

**Intent**: State the ADR's layering and dependency-direction invariants (domain has zero imports from application/adapters; application imports domain only; adapters depend on domain+application; nothing upstream imports a concrete adapter) plus the directory-convention sketch and the InMemoryFirst rule, as directives an agent follows while writing backend code.

**Contract**: Frontmatter block used by all four files:
```yaml
---
description: <one line>
paths: ["backend/**"]
globs: backend/**
alwaysApply: false
---
```
Body cites `context/adrs/hexagonal-arch-shape/decision.md` for rationale rather than restating it.

**File**: `context/foundation/rules/cqrs-lite.md`

**Intent**: State the commands/queries split, the `UnitOfWork` port as the exclusive commit boundary (`async with uow: ...; await uow.commit()`, default rollback), queries never receiving a `UnitOfWork`, DTOs as data-only Pydantic models returned as-is by output adapters, and constructor-injection dispatch (no bus).

**Contract**: Same shared frontmatter shape as above; `paths`/`globs` scoped to `backend/**`.

**File**: `context/foundation/rules/contract-testing.md`

**Intent**: State the InMemoryFirst pairing and the one-contract-per-port rule, parametrized over adapter implementations, with in-memory mandatory on every CI run and real/LLM-backed adapters on a separate non-blocking cadence.

**Contract**: Same shared frontmatter shape.

**File**: `context/foundation/rules/exceptions.md`

**Intent**: State that domain/application exceptions share the `CoreException` root (never `DomainException`), the auto-derived overridable `code`, that only the HTTP input adapter owns the `code -> status` mapping and never imports a concrete domain/application exception class, and that domain/application never import `FastAPI`/`HTTPException`. Points at `backend/src/domain/exceptions.py` and `backend/src/adapters/http/errors.py` as the concrete implementation this rule governs.

**Contract**: Same shared frontmatter shape; also names the exhaustiveness-test requirement (walk `CoreException.__subclasses__()` recursively, assert full + collision-free mapping).

#### 2. Per-ecosystem symlinks

**File**: `.claude/rules/layering.md`, `.claude/rules/cqrs-lite.md`, `.claude/rules/contract-testing.md`, `.claude/rules/exceptions.md`

**Intent**: Expose the canonical docs to Claude Code without duplicating content.

**Contract**: Each is `ln -s ../../context/foundation/rules/<topic>.md .claude/rules/<topic>.md` (relative symlink, so the pair stays valid regardless of checkout location).

**File**: `.cursor/rules/layering.mdc`, `.cursor/rules/cqrs-lite.mdc`, `.cursor/rules/contract-testing.mdc`, `.cursor/rules/exceptions.mdc`

**Intent**: Expose the same canonical docs to Cursor. The symlink's own name carries the `.mdc` extension Cursor requires; the target keeps its canonical `.md` name.

**Contract**: Each is `ln -s ../../context/foundation/rules/<topic>.md .cursor/rules/<topic>.mdc`.

### Success Criteria:

#### Automated Verification:
- `find .claude/rules .cursor/rules -maxdepth 1 -type l -newer context/foundation/rules -print` lists all 8 new symlinks
- `readlink -f .claude/rules/exceptions.md` and `readlink -f .cursor/rules/exceptions.mdc` both resolve to `context/foundation/rules/exceptions.md` (repeat per topic)
- A YAML parse of each canonical file's frontmatter succeeds (e.g. `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]).read().split('---')[1])" context/foundation/rules/layering.md`) and contains all four keys (`description`, `paths`, `globs`, `alwaysApply`)

#### Manual Verification:
- In a fresh Claude Code session in this repo, `Read backend/src/main.py`, then run `/context` and confirm at least one `context/foundation/rules/*.md` file (via its `.claude/rules/*.md` symlink) appears under Memory files
- Open the repo in Cursor, open a file under `backend/`, and confirm the path-scoped rules show as active (Cursor's rules indicator)

---

## Phase 2: `CoreException` stubs

### Overview

Materialize the `CoreException` symbol Phase 3's tests import, with no derivation logic yet.

### Changes Required:

#### 1. Exception base class shape

**File**: `backend/src/domain/exceptions.py`

**Intent**: Give later phases (and any future domain/application code) a stable import target for the shared exception root, ahead of the derivation behavior.

**Contract**: Exports `CoreException(Exception)` with a `code() -> str` classmethod raising `NotImplementedError` for now, and a class-level `_code: ClassVar[str]` slot subclasses may set to override derivation.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` passes with the new module
- `cd backend && uv run ruff check .` passes

---

## Phase 3: `CoreException` behavior

### Overview

Implement the auto-derivation of `code` from the subclass name, and the explicit-override path.

### Changes Required:

#### 1. Code derivation

**File**: `backend/src/domain/exceptions.py`

**Intent**: Every `CoreException` subclass gets a machine-readable `code` for free (snake_case of its own name, minus a trailing `Error`/`Exception`), unless it sets `_code` explicitly in its own class body.

**Contract**: `__init_subclass__` sets `cls._code` from `cls.__name__` only when `"_code" not in cls.__dict__` at subclass-creation time — the check that makes an explicit override in the subclass body win over the auto-derivation:
```python
def __init_subclass__(cls, **kwargs: object) -> None:
    super().__init_subclass__(**kwargs)
    if "_code" not in cls.__dict__:
        cls._code = _to_snake_case(cls.__name__)
```
`code()` returns `cls._code`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/test_exceptions.py -v` — covers: default derivation (e.g. `NoteNotFoundError` -> `note_not_found`, matching the ADR's own worked example), trailing-`Error`/`Exception` stripping, multi-word class names, and explicit `_code` override winning over derivation
- `cd backend && uv run basedpyright && uv run ruff check .`

---

## Phase 4: HTTP exception-mapping stubs

### Overview

Materialize the mapping table and handler shapes Phase 5's tests import, with no real entries or logic yet.

### Changes Required:

#### 1. Mapping table and handler shape

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Give the input adapter its one designated place to own `code -> status` mapping, and a handler shape FastAPI can register, ahead of any real entries.

**Contract**: Exports `EXCEPTION_STATUS_MAP: dict[str, int] = {}` and `async def core_exception_handler(request: Request, exc: CoreException) -> JSONResponse`, body `raise NotImplementedError` for now. Imports only `CoreException` (never a concrete subclass) per the ADR's "never imports a concrete domain/application exception class" rule.

#### 2. Registration

**File**: `backend/src/main.py`

**Intent**: Wire the handler so any `CoreException` raised anywhere in the app is translated at the HTTP boundary.

**Contract**: `app.add_exception_handler(CoreException, core_exception_handler)`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright && uv run ruff check .`

---

## Phase 5: HTTP exception-mapping behavior and exhaustiveness test

### Overview

Implement the real mapping/handler behavior, add one representative subclass so the exhaustiveness test is meaningful, and implement that test.

### Changes Required:

#### 1. Representative subclass

**File**: `backend/src/domain/exceptions.py`

**Intent**: A generic, broadly reusable `CoreException` subclass every future bounded context can raise, existing here purely so Phase 5's exhaustiveness test has at least one real case to check rather than passing vacuously.

**Contract**: `class NotFoundError(CoreException): ...` — no body beyond `pass`; derives `code() == "not_found"` via Phase 3's mechanism.

#### 2. Mapping and handler behavior

**File**: `backend/src/adapters/http/errors.py`

**Intent**: `NotFoundError` maps to HTTP 404; any `CoreException` translates into a JSON body carrying its `code` and message; an unmapped code (should never happen once the exhaustiveness test is green) still degrades to 500 rather than crashing the handler.

**Contract**:
```python
EXCEPTION_STATUS_MAP: dict[str, int] = {"not_found": 404}

async def core_exception_handler(request: Request, exc: CoreException) -> JSONResponse:
    status_code = EXCEPTION_STATUS_MAP.get(exc.code(), 500)
    return JSONResponse(status_code=status_code, content={"code": exc.code(), "detail": str(exc)})
```

#### 3. Exhaustiveness test

**File**: `backend/tests/unit/test_http_error_mapping.py`

**Intent**: Recover, as a test, the exhaustiveness guarantee a closed enum would have given the type checker for free — per the ADR amendment's stated tradeoff.

**Contract**: A recursive `CoreException.__subclasses__()` walk asserts (a) every discovered subclass's `code()` is a key in `EXCEPTION_STATUS_MAP`, and (b) no two subclasses share the same `code()`. Plus one direct-call test of `core_exception_handler` with a `NotFoundError` instance, asserting `status_code == 404` and the JSON body's `code == "not_found"`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/test_http_error_mapping.py -v`
- `cd backend && uv run pytest` (full suite still green)
- `cd backend && uv run basedpyright && uv run ruff check .`

---

## Testing Strategy

### Unit Tests:
`tests/unit/test_exceptions.py` (Phase 3), `tests/unit/test_http_error_mapping.py` (Phase 5) — both pure/unit-level, no I/O.

### Integration Tests:
None required — the handler is exercised via direct call, not a live route, since no endpoint raises a domain exception yet.

### Manual Testing Steps:
Phase 1's two Manual Verification bullets (Claude Code `/context` check, Cursor active-rules check).

## Performance Considerations

None — rule documents and exception scaffolding carry no runtime cost.

## Migration Notes

None — purely additive; no existing behavior changes.

## References

- `context/adrs/hexagonal-arch-shape/decision.md` (incl. "Amendment (2026-08-28)")
- `context/foundation/README.md`
- Progress and execution state: `todos.md`
