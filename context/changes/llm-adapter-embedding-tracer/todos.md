---
change_id: llm-adapter-embedding-tracer
current_phase: 1
next_step: 1.1
next_command: /implement llm-adapter-embedding-tracer phase 1
updated: 2026-09-11
---

### Phase 1: Provider and telemetry dependencies, settings, environment

#### Automated

- [ ] 1.1 Pin pydantic-ai-slim[openai]==2.39.0 and the three OpenTelemetry packages at ==1.44.0
- [ ] 1.2 Add an RFC 3339 exclude-newer cutoff to [tool.uv] and prove it is enforced
- [ ] 1.3 Declare EmbeddingProvider enum and provider, model, and Langfuse settings fields
- [ ] 1.4 Record the new environment keys in .env.example

#### Manual

- [ ] 1.5 Confirm Settings() defaults to the openrouter provider with no .env override

### Phase 2: `adapters/out/llm/` stubs and interfaces

#### Automated

- [ ] 2.1 Create the adapters/out/llm package with the tracing helper signatures and attribute constants
- [ ] 2.2 Add the OpenRouterEmbeddingAdapter stub with its constructor and embed signature

#### Manual

- [ ] 2.3 Run the existing suite and confirm the stubs changed nothing

### Phase 3: Adapter behaviour and span emission

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 Map the provider vector into Embedding through Embedder.embed_query
- [ ] 3.2 Pass the configured dimensions through EmbeddingSettings only when set
- [ ] 3.3 Emit one observation span per embed with the Langfuse attribute vocabulary
- [ ] 3.4 Mark the span ERROR on provider failure and let the exception propagate unchanged

#### Manual

- [ ] 3.5 Read the new test names and confirm they describe behaviour, not implementation shape

### Phase 4: Telemetry bootstrap and composition wiring

#### Automated

- [ ] 4.1 Add adapters/telemetry.py with configure_tracing and the Langfuse OTLP exporter
- [ ] 4.2 Honour embedding_provider in compose.py and start tracing before adapters are built
- [ ] 4.3 Pin the test environment to the deterministic provider with tracing off

#### Manual

- [ ] 4.4 Start the backend with tracing off, then with real Langfuse keys, and confirm no exporter errors

### Phase 5: Smoke script

#### Automated

- [ ] 5.1 Add scripts/smoke_embedding.py with an explicit force_flush before exit

#### Manual

- [ ] 5.2 Run the smoke script against real OpenRouter and record the printed dimension
- [ ] 5.3 Re-run with EMBEDDING_DIMENSIONS=256 and record whether OpenRouter honoured it
- [ ] 5.4 Confirm the observation appears in the Langfuse project with input and model visible

### Phase 6: Langfuse MCP for Claude Code and Cursor

#### Automated

- [ ] 6.1 Add .mcp.json pointing at the hosted Langfuse MCP endpoint
- [ ] 6.2 Add .cursor/mcp.json with the same server
- [ ] 6.3 Document LANGFUSE_MCP_AUTH derivation in .env.example and README

#### Manual

- [ ] 6.4 Confirm /mcp in Claude Code lists langfuse connected and returns recent observations
- [ ] 6.5 Confirm Cursor connects and record whether it expanded the header variable
