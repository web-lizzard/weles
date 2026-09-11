---
date: 2026-09-11T20:42:00+02:00
topic: "Pydantic AI as the outbound LLM adapter library"
topic_slug: pydantic-ai
container_id: llm-adapter
tags: [research, pydantic-ai, llm-adapter, capture-flow, hexagonal]
last_updated: 2026-09-11
---

# Research: Pydantic AI as the outbound LLM adapter library

## Research Question

`/research --topic pydantic-ai llm-adapter` — Potrzebuję, abyś wyciągnął dane na temat biblioteki, której będziemy używać jako adapter.

## Summary

**Pydantic AI** (`pydantic_ai`) is the stack-chosen Python agent framework for LLM integration. It centers on an `Agent` bound to a model (`provider:model` strings or concrete model classes), optional structured `output_type` (Pydantic models and scalars), and dependency injection via `deps_type` / `RunContext` for tools and dynamic prompts. Async completion uses `await agent.run(...)` → `AgentRunResult`; streaming text uses `async with agent.run_stream(...) as response` and `async for text in response.stream_text()`.

In this repository, **`pydantic-ai-slim`** is already a runtime dependency (resolved to 2.35.3 in the lockfile) but **no production code imports it yet**. Architecture rules confine `pydantic-ai` to **outbound adapters** under `adapters/out/llm/` (capture’s socratic plan names `adapters/out/llm/capture/`). Application ports are already defined and backed by deterministic in-memory adapters with parametrized contract tests—the real Pydantic AI adapters must satisfy those contracts without changing port signatures.

Prefer **`pydantic-ai-slim[<provider extras>]`** over the full `pydantic-ai` meta-package until optional surfaces (CLI, MCP, evals, web UI, bundled Logfire) are needed. Testing without live models uses **`TestModel`**, **`FunctionModel`**, **`Agent.override`**, and **`ALLOW_MODEL_REQUESTS=False`**. License: MIT; Python ≥3.10 (backend requires ≥3.12).

## Findings

### Repository posture

- ADRs commit the backend to **Pydantic AI** for LLM work and **hexagonal isolation** partly because LLM adapters are slow and costly in CI (`context/adrs/repo-shape/decision.md`, `context/adrs/hexagonal-arch-shape/decision.md`).
- **Domain** and **application** must not import `pydantic-ai`; only adapters may (`context/adrs/hexagonal-arch-shape/decision.md:18`, `context/foundation/rules/layering.md:16-18`).
- **InMemoryFirst** and **contract testing**: every port has in-memory adapters on every CI run; LLM-backed adapters run the same contract suite on a **non-blocking** cadence (`context/adrs/hexagonal-arch-shape/decision.md:31-33`).
- Bootstrap added **`pydantic-ai-slim>=0.0.14`** without `[web]` extras until call sites exist (`context/archive/changes/2026-08-28-backend-bootstrap/plan-brief.md:54`).

### First integration targets (capture)

- **`TopicExtractionPort`**: `async def extract(first_message: MessageContent) -> SessionTopic` (`backend/src/application/capture/ports.py:21-22`).
- **`ConfidenceAssessmentPort`**: `async def assess(transcript: Transcript) -> ConfidenceAssessment` (`backend/src/application/capture/ports.py:25-26`).
- **`ReplyGenerationPort`**: `def generate(...) -> AsyncIterator[ReplyChunk]` (`backend/src/application/capture/ports.py:29-32`); `send_message` consumes via `async for chunk` (`backend/src/application/capture/commands/send_message.py:100`).
- Deterministic stand-ins live under `backend/src/adapters/out/in_memory/capture/` and are wired in `backend/src/adapters/compose.py:135-137`.
- The socratic capture plan deferred real adapters so swapping to Pydantic AI should touch **only** `adapters/out/llm/capture/` (`context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md:7`).

### Pydantic AI library surface

- **`Agent`** is the primary orchestration type: instructions, tools, `output_type`, `deps_type`, default model (`https://ai.pydantic.dev/agents/`).
- **Models** use `provider:model` (e.g. `openai:gpt-5.2`) or provider-specific classes; **`infer_model("test")`** resolves to **`TestModel`** (`https://ai.pydantic.dev/models/`, `https://ai.pydantic.dev/api/models/base/`).
- **Structured output**: set `output_type` on the agent; default path uses tool calling; result in **`AgentRunResult.output`** (`https://ai.pydantic.dev/output/`).
- **Streaming**: **`Agent.run_stream`** yields **`StreamedRunResult`**; **`stream_text()`** returns **`AsyncIterator[str]`**; **`stream_output()`** streams partial structured output (`https://ai.pydantic.dev/api/agent/`, `https://ai.pydantic.dev/api/result/`). Docs note that with non-text `output_type`, `run_stream` may stop at the first final output—relevant if tools are added later.
- **Dependencies**: `deps_type` + `RunContext[DepsT]` in tools and dynamic system prompts (`https://ai.pydantic.dev/dependencies/`).
- **`pydantic-ai-slim`**: install only needed provider extras (e.g. `pydantic-ai-slim[openai]`); full **`pydantic-ai`** bundles more providers and tooling (`https://ai.pydantic.dev/install/#slim-install`).
- **Testing**: `TestModel` (schema-shaped fake output), `FunctionModel` (custom `ModelResponse` handler), `Agent.override`, global **`ALLOW_MODEL_REQUESTS=False`** (`https://ai.pydantic.dev/testing/`).

### Suggested adapter boundary

- Application ports stay free of `Agent`, `AgentRunResult`, and provider SDK types.
- Adapter module constructs or receives a configured `Agent` (model string from settings), maps port inputs to prompts/history, calls `run` or `run_stream`, maps `output` / streamed chunks to domain/application value objects (`SessionTopic`, `ConfidenceAssessment`, `ReplyChunk`).
- Adapter tests use `TestModel` / `FunctionModel`; application tests continue to mock ports.

## Code References

- `backend/pyproject.toml:14` — `pydantic-ai-slim>=0.0.14` runtime dependency
- `backend/src/application/capture/ports.py:21-32` — capture LLM port protocols
- `backend/src/application/capture/commands/send_message.py:52-54` — port injection in send-message command
- `backend/src/application/capture/commands/send_message.py:84-100` — extract, assess, generate call sequence
- `backend/src/adapters/compose.py:135-137` — deterministic capture LLM adapters wired today
- `backend/src/adapters/out/in_memory/capture/topic_extraction.py:7-11` — deterministic topic extraction
- `backend/src/adapters/out/in_memory/capture/confidence_assessment.py:10-17` — deterministic confidence assessment
- `backend/src/adapters/out/in_memory/capture/reply_generation.py:35-40` — deterministic reply streaming
- `backend/tests/unit/capture/contracts/test_topic_extraction_contract.py:11-12` — contract parametrization (deterministic only today)
- `backend/tests/unit/capture/contracts/test_confidence_assessment_contract.py:12-13` — contract parametrization
- `backend/tests/unit/capture/contracts/test_reply_generation_contract.py:21-22` — contract parametrization
- `context/adrs/hexagonal-arch-shape/decision.md:5` — LLM cost motivates hex isolation
- `context/adrs/hexagonal-arch-shape/decision.md:18` — domain must not import `pydantic-ai`
- `context/adrs/hexagonal-arch-shape/decision.md:43` — `adapters/out/.../llm/` directory sketch
- `context/adrs/backend-stack/decision.md:3` — carries `pydantic-ai` from repo-shape ADR
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md:7` — swap boundary `adapters/out/llm/capture/`
- `context/archive/changes/2026-08-28-backend-bootstrap/plan-brief.md:54` — slim without `[web]` until call sites

## External References

- <https://ai.pydantic.dev/> — official documentation home
- <https://ai.pydantic.dev/agents/> — “Agents are Pydantic AI's primary interface for interacting with LLMs.”
- <https://ai.pydantic.dev/install/#slim-install> — `pydantic-ai-slim` and provider extras
- <https://ai.pydantic.dev/models/> — model providers and `provider:model` naming
- <https://ai.pydantic.dev/output/> — structured output via `output_type` and `AgentRunResult`
- <https://ai.pydantic.dev/api/agent/> — `run`, `run_stream`, `run_sync`, `run_stream_events`, `iter`
- <https://ai.pydantic.dev/api/result/> — `StreamedRunResult.stream_text`, `stream_output`, `get_output`
- <https://ai.pydantic.dev/dependencies/> — `deps_type`, `RunContext`, dependency injection for tools and prompts
- <https://ai.pydantic.dev/testing/> — `TestModel`, `FunctionModel`, `Agent.override`, `ALLOW_MODEL_REQUESTS`
- <https://github.com/pydantic/pydantic-ai/blob/main/LICENSE> — MIT License, Pydantic Services Inc.
- <https://github.com/pydantic/pydantic-ai/blob/main/pyproject.toml> — `requires-python = ">=3.10"`, Production/Stable classifier

## Open Questions

- Which **provider extra(s)** to add to `pydantic-ai-slim` (OpenAI, Anthropic, OpenRouter, local OpenAI-compatible API)?
- **Distill and embedding** ports (`CardGeneration`, `EmbeddingPort`): separate agents per port vs shared adapter factory?
- **Configuration**: model id, API keys, `usage_limits`, and timeouts—`pydantic-settings` shape and compose wiring?
- **Observability**: adopt Logfire (`logfire` extra) in the first slice or defer?
