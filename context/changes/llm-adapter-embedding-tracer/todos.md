---
change_id: llm-adapter-embedding-tracer
current_phase: 6
next_step:
next_command: /archive llm-adapter-embedding-tracer
updated: 2026-09-12
---

### Phase 1: Provider and telemetry dependencies, settings, environment

#### Automated

- [x] 1.1 Pin pydantic-ai-slim[openai]==2.39.0 and the three OpenTelemetry packages at ==1.44.0
- [x] 1.2 Add an RFC 3339 exclude-newer cutoff to [tool.uv] and prove it is enforced
- [x] 1.3 Declare EmbeddingProvider enum and provider, model, and Langfuse settings fields
- [x] 1.4 Record the new environment keys in backend/.env.example

#### Manual

- [x] 1.5 Confirm Settings() defaults to the openrouter provider with no .env override — aab6507

### Phase 2: `adapters/out/llm/` stubs and interfaces

#### Automated

- [x] 2.1 Create the adapters/out/llm package with the tracing helper signatures and attribute constants — 3231051
- [x] 2.2 Add the OpenRouterEmbeddingAdapter stub with its constructor and embed signature — 3231051

#### Manual

- [x] 2.3 Run the existing suite and confirm the stubs changed nothing — 3231051

### Phase 3: Adapter behaviour and span emission

#### Tests

- [x] tests generated — 12cbced

#### Automated

- [x] 3.1 Map the provider vector into Embedding through Embedder.embed_query — 9fe8498
- [x] 3.2 Pass the configured dimensions through EmbeddingSettings only when set — 9fe8498
- [x] 3.3 Emit one observation span per embed with the Langfuse attribute vocabulary — 9fe8498
- [x] 3.4 Mark the span ERROR on provider failure and let the exception propagate unchanged — 9fe8498

#### Manual

- [x] 3.5 Read the new test names and confirm they describe behaviour, not implementation shape — 9fe8498

### Phase 4: Telemetry bootstrap and composition wiring

#### Automated

- [x] 4.1 Add adapters/telemetry.py with configure_tracing and the Langfuse OTLP exporter — a53c8a2
- [x] 4.2 Honour embedding_provider in compose.py and start tracing before adapters are built — a53c8a2
- [x] 4.3 Pin the test environment to the deterministic provider with tracing off — a53c8a2

#### Manual

- [x] 4.4 Start the backend with tracing off, then with real Langfuse keys, and confirm no exporter errors — a53c8a2

### Phase 5: Smoke script

#### Automated

- [x] 5.1 Add scripts/smoke_embedding.py with an explicit force_flush before exit — 61b6958

#### Manual

- [x] 5.2 Run the smoke script against real OpenRouter and record the printed dimension
- [x] 5.3 Re-run with EMBEDDING_DIMENSIONS=256 and record whether OpenRouter honoured it
- [x] 5.4 Confirm the observation appears in the Langfuse project with input and model visible

### Phase 6: Langfuse MCP for Claude Code and Cursor

#### Automated

- [x] 6.1 Add .mcp.json pointing at the hosted Langfuse MCP endpoint
- [x] 6.2 Add .cursor/mcp.json with the same server
- [x] 6.3 Document LANGFUSE_MCP_AUTH derivation in .env.example and README

#### Manual

- [x] 6.4 Confirm /mcp in Claude Code lists langfuse connected and returns recent observations
- [x] 6.5 Confirm Cursor connects and record whether it expanded the header variable
