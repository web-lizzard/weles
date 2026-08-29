---
change_id: code-quality
title: Code quality
status: implementing
created: 2026-08-28
updated: 2026-08-29
archived_at: null
---

## Notes

Wire up ruff (lint+format) and basedpyright (replacing the unconfigured mypy dependency) for the backend, and Biome for the TUI, each configured and cleaned to a passing baseline, then enforced via blocking pre-commit hooks. CI is explicitly out of scope. See `plan.md` / `plan-brief.md`.
