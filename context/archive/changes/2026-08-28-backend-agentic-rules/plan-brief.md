# Backend Agentic Rules — Plan Brief

> Full plan: `plan.md`

## What & Why

Turn the `hexagonal-arch-shape` ADR's invariants into rule files that Claude Code and Cursor both load automatically while working in `backend/`, so the architecture is enforced during ordinary coding sessions rather than only at review time. Bootstrap the one concrete mechanism the ADR's amendment names: `CoreException`.

## Starting Point

Backend is a bare hexagonal scaffold — no exception hierarchy in code yet. Both rule ecosystems (`.claude/rules/`, `.cursor/rules/`) already exist with one topic (`language-policy`), giving a precedent to extend rather than a greenfield format decision.

## Desired End State

Four topic rule files, authored once and symlinked into both `.claude/rules/*.md` and `.cursor/rules/*.mdc`, auto-load when either tool touches a file under `backend/**`. `CoreException` exists with auto-derived, overridable `code`, and the HTTP adapter has one exhaustively-tested `code -> status` mapping table.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Rule granularity | 4 topic files (layering, cqrs-lite, contract-testing, exceptions) | Matches the ADR's own section boundaries; each can be scoped/extended independently | Session |
| Canonical storage location | `context/foundation/rules/`, not `.ordo/rules/` | `.ordo/` is entirely package-manager-owned (lock.json tracks it); `context/foundation/` is explicitly for cross-change living docs | Plan |
| Cross-ecosystem sharing | One file per topic, symlinked into both `.claude/rules/*.md` and `.cursor/rules/*.mdc` with a unified frontmatter block | Both tools officially document symlink-sharing; zero drift between what each tool enforces | Session + Research |
| Activation scope | Path-scoped to `backend/**` (Claude `paths:`, Cursor `globs:`) | User chose path-scoping over always-on, to avoid noise while working on the TUI | Session |
| `CoreException` bootstrap depth | Base class + exhaustiveness test + adapter mapping skeleton, plus one representative subclass (`NotFoundError`) | Confirmed by user; without a real subclass the exhaustiveness test is vacuous | Session |

## Scope

**In scope:** 4 canonical rule docs + 8 symlinks; `CoreException` with derived/overridable `code`; one representative subclass; HTTP adapter mapping table, handler, and exhaustiveness test.

**Out of scope:** `context/foundation/architecture.md`; any bounded-context-specific exceptions module; an exception catalog beyond the one representative subclass; contract-test suites (no ports/adapters exist yet to test); TUI or root `CLAUDE.md` changes.

## Architecture / Approach

One authored copy per rule topic lives at `context/foundation/rules/<topic>.md`; `.claude/rules/<topic>.md` and `.cursor/rules/<topic>.mdc` are symlinks to it, so editing the canonical file updates both ecosystems atomically. `CoreException` follows the plan's stubs-then-behavior split: shape first, `__init_subclass__`-driven derivation and the exhaustiveness test together as the TDD'd behavior.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Rules content + wiring | 4 canonical docs, 8 symlinks, path-scoped to `backend/**` | Unified frontmatter (Claude's `paths` + Cursor's `globs`/`description`/`alwaysApply` in one file) is unverified until Phase 1's manual check runs in both tools |
| 2. `CoreException` stubs | Importable class shape | — |
| 3. `CoreException` behavior | Auto-derived + overridable `code` | Snake-case derivation edge cases (acronyms, digits) |
| 4. HTTP mapping stubs | Importable mapping/handler shape | — |
| 5. HTTP mapping behavior + exhaustiveness test | `NotFoundError` -> 404, exhaustive code/status test | None once Phase 3 lands |

**Prerequisites:** None — backend scaffold already exists.
**Estimated effort:** Small — one docs phase, two TDD unit pairs.

## Open Risks & Assumptions

- Claude Code's path-scoped rules reload only when a matching file is *read*, not on file *creation* — a documented limitation, not expected to matter here since `backend/**` already has files routinely read, but worth remembering if a rule ever seems inactive on a brand-new file.
- Cursor's exact tolerance for unrecognized frontmatter keys is assumed, not independently documented for this specific combination — Phase 1's manual verification is the actual check.

## Success Criteria (Summary)

- Both `.claude/rules/*.md` and `.cursor/rules/*.mdc` resolve (via symlink) to the same canonical file per topic, and each activates only under `backend/**`.
- `CoreException` subclasses get a correct, overridable `code` (unit-tested).
- Every `CoreException` subclass has a mapped HTTP status; the exhaustiveness test fails on any gap or collision.
