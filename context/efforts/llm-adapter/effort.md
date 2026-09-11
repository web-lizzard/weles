---
effort_id: llm-adapter
title: Llm adapter
status: active
created: 2026-09-11
updated: 2026-09-11
archived_at: null
---

## Goal

Make the domain the command centre over the LLM. Weles's five generative seams run today on deterministic in-memory adapters, with all model-facing policy either absent or implicit in those stubs. This effort moves that policy into `domain/` — transition graphs, instructions with declared context requirements, and tool definitions that speak domain vocabulary and call domain functions — and adds `adapters/out/llm/` to render and invoke it against a real provider, traced in Langfuse. It succeeds when capture and distill run end to end on a real model, the policy layer is covered by model-free unit tests, and replacing pydantic-ai would require no change under `domain/`.
