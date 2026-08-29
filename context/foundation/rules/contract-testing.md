---
description: Contract-test requirements for ports and adapters under backend/
paths: ["backend/**"]
globs: backend/**
alwaysApply: false
---

# Contract testing

Full rationale: `context/adrs/hexagonal-arch-shape/decision.md`.

## One contract per port

Each port has one behavioral contract-test suite, parametrized over its adapter implementations.

## Cadence by adapter cost

- The in-memory implementation runs that suite on **every CI invocation** — mandatory.
- Real, especially LLM-backed, adapters run the same suite on a separate, **non-blocking** cadence (on-demand or scheduled) rather than gating ordinary CI.

The contract must exist and be runnable against any adapter; only its CI cadence differs by adapter cost.
