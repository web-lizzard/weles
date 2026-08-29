---
description: CoreException hierarchy and HTTP code-to-status mapping for backend/
paths: ["backend/**"]
globs: backend/**
alwaysApply: false
---

# Exceptions

Full rationale: `context/adrs/hexagonal-arch-shape/decision.md` (incl. "Amendment (2026-08-28)").

## Shared root

Domain and application exceptions share one root, `CoreException(Exception)` — deliberately not `DomainException`, so an application-layer exception inheriting from it doesn't misread as a domain concept. Implemented in `backend/src/domain/exceptions.py`.

## Auto-derived `code`

`CoreException` derives a default machine-readable `code` from its own subclass name via snake_case (e.g. `NoteNotFoundError` → `note_not_found`, stripping a trailing `Error`/`Exception`). A subclass overrides `code` explicitly only when the derived value isn't the one wanted (two classes sharing a code, or decoupling the code from a class rename).

Renaming an exception class silently changes its wire-visible `code` unless the author pins `code` explicitly on rename.

## Mapping ownership

Only the HTTP input adapter owns the one `code -> status` mapping table, implemented in `backend/src/adapters/http/errors.py`. It never imports a concrete domain/application exception class — only `CoreException.code()` values cross that boundary. Domain and application code never import `FastAPI`/`HTTPException` or any transport-specific error type.

## Exhaustiveness test

A test walks `CoreException.__subclasses__()` recursively and asserts every discovered `code` has an entry in the adapter's mapping table, and that no two subclasses collide on the same `code` — the exhaustiveness a closed enum would have given for free, recovered here as a test instead of a type-checker guarantee.
