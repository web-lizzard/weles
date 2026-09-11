# Vocabulary Reuse on a Real Embedding Model, Traced in Langfuse — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-01 of the `llm-adapter` effort swaps vocabulary reuse from a sha512 stand-in onto
`openai/text-embedding-3-small` reached through OpenRouter, with every call visible as a
Langfuse observation. `EmbeddingPort` has no policy surface, so it proves the outbound LLM
seam at the lowest cost — and the package, provider wiring, and tracing that land here are
inherited by every later slice.

## Starting Point

`DeterministicEmbeddingAdapter` hashes text into 32 dimensions and cannot fail;
`adapters/out/llm/` does not exist and nothing in the tree configures OpenTelemetry.
`pydantic-ai-slim` resolves to 2.35.3 — embeddings are already there — but without the
`[openai]` extra that its OpenAI embedding module needs.

## Desired End State

The backend embeds through OpenRouter by default, each `embed` emits one OpenTelemetry span
that Langfuse renders as an embedding observation, a smoke script proves the round trip
against the real provider, and both Claude Code and Cursor can query that Langfuse project
over MCP.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Provider | OpenRouter for embeddings and later chat | One key and one billing surface across the whole effort. | Plan |
| Library | pydantic-ai `Embedder` + `OpenAIEmbeddingModel` + `OpenRouterProvider` | Already a dependency and already ADR-committed for LLM adapters. | Research |
| Extra | `pydantic-ai-slim[openai]`, not `[openrouter]` | The OpenAI embeddings module imports `tiktoken` at import time, which `[openrouter]` does not pull. | Research |
| Tracing dependency | OpenTelemetry API in adapters; Langfuse only at composition | Adapters stay vendor-neutral, and a future domain-side span port reuses the same vocabulary. | Plan |
| Langfuse hosting | Cloud Hobby, tracing only | Zero infra, and one observation per embed stays far under the 50k unit cap. | Research |
| Granularity | One observation per `embed()` | Nests naturally under a conversation trace in S-05 without doubling billable units. | Plan |
| Model and dimensions | Both configurable; `dimensions` unset by default | Lets the smoke script settle empirically whether OpenRouter honours a reduction. | Plan |
| Adapter selection | Explicit `embedding_provider` switch, default `openrouter`, pinned to `deterministic` in tests | No environment starts spending tokens by accident, and CI never touches the network. | Plan |
| Error handling | Dropped from this slice | A failure taxonomy across all five seams is designed later, not from the one seam with no policy surface. | Plan |
| Contract suite | Not extended in this slice | Author's call: the smoke script is the proof here, against the roadmap's stated intent. | Plan |
| MCP | Langfuse's hosted endpoint, configs committed with `${LANGFUSE_MCP_AUTH}` | First-party, install-free, and no secret enters the repository. | Research |

## Scope

**In scope:** provider and telemetry dependencies; settings; `adapters/out/llm/` with a
tracing helper and the OpenRouter embedding adapter; unit tests with no network; telemetry
bootstrap and composition wiring; a smoke script; MCP configuration for Claude Code and
Cursor.

**Out of scope:** an entry in the embedding contract suite; any error contract, retry, or
fallback; changes to `send_message.py` or the SSE event contract; blanket OTEL
auto-instrumentation; Langfuse scores, datasets, prompts, or evaluation; self-hosted
Langfuse; threshold retuning; the other four LLM seams.

## Architecture / Approach

```
compose.py ──reads──> Settings.embedding_provider
    │                      │
    │                      ├─ deterministic ─> DeterministicEmbeddingAdapter
    │                      └─ openrouter ────> OpenRouterEmbeddingAdapter
    │                                              │ uses
    │                                              ├─ pydantic-ai Embedder ──> OpenRouter
    │                                              └─ adapters/out/llm/tracing (OTel API only)
    └──calls──> adapters/telemetry.configure_tracing()
                     └─ TracerProvider + OTLP exporter ──> Langfuse Cloud
```

Adapters know OpenTelemetry; only `adapters/telemetry.py` knows Langfuse.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Dependencies, settings, environment | `[openai]` extra, OTel packages, every new config field | The lock's loose `>=0.0.14` bound hides how new the real requirement is |
| 2. `adapters/out/llm/` stubs | Tracing helper and adapter signatures Phase 3 imports | Attribute vocabulary chosen here is inherited by four later seams |
| 3. Adapter behaviour and span emission | Vector mapping, dimension setting, one Langfuse-shaped span per call | Span attribute names must match Langfuse's mapping exactly or the observation renders blank |
| 4. Telemetry bootstrap and wiring | OTLP exporter to Langfuse, provider switch honoured | A default-on provider reaching the test suite or CI |
| 5. Smoke script | One real embed, one real trace, run by hand | `BatchSpanProcessor` silently drops the span without an explicit flush |
| 6. Langfuse MCP for both editors | `.mcp.json` and `.cursor/mcp.json` against the hosted endpoint | Cursor's `${VAR}` expansion in headers is undocumented |

**Prerequisites:** an OpenRouter account with credit, and a Langfuse Cloud Hobby project (EU
region assumed) with its public and secret keys.

**Estimated effort:** small. Six phases, one of which carries tests; the bulk is
configuration, wiring, and two verification surfaces.

## Open Risks & Assumptions

- **Reuse behaviour will shift.** `vocabulary_match_threshold = 0.85` was tuned for hashed
  vectors, where unrelated texts are near-orthogonal; real embeddings of short labels cluster
  much higher. The slice does not retune it — expect over-eager reuse and treat the first
  manual capture session as the measurement.
- **A mid-draft embedding failure truncates the SSE stream.** `resolve_topic` runs inside the
  streaming generator, headers are already sent, and no error contract exists in this slice.
  Accepted knowingly; S-05 owns the fix.
- **Provider exceptions reach the HTTP edge as OpenAI SDK types**, which is a layering
  violation for as long as it stands. Deferred with the error taxonomy, not overlooked.
- **OpenRouter's support for the `dimensions` parameter is undocumented.** The smoke script
  prints the returned dimension, which settles it in one run.
- **Langfuse recommends its own SDK for Python** and documents the bare-OTel path for other
  languages. The ingestion contract is protocol-level, so this works — but there is no
  first-party Python sample to copy, and attribute names must be taken from the mapping table.
- **Latency is now user-visible.** Four sequential provider calls per draft, inside a stream
  the user is watching.

## Success Criteria (Summary)

- `uv run python scripts/smoke_embedding.py "TCP handshakes"` prints a real vector dimension
  and the matching observation appears in Langfuse within seconds.
- A capture draft through the TUI produces one Langfuse observation per resolved topic and
  tag label, with no code under `domain/` or `application/` changed.
- The full test suite passes with no API keys present and makes no network call.
