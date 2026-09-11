# Vocabulary Reuse on a Real Embedding Model, Traced in Langfuse — Implementation Plan

## Overview

Slice S-01 of the `llm-adapter` effort. `EmbeddingPort` is the one seam in the port
inventory with no policy surface, so it proves the outbound LLM seam end to end at the
lowest cost: the `adapters/out/llm/` package, the provider extras and settings, and
distributed tracing all land here, and every later slice inherits them.

Vocabulary reuse stops running on a hashed stand-in and starts running on
`openai/text-embedding-3-small` reached through OpenRouter via pydantic-ai. Every embedding
call becomes one observation visible in Langfuse Cloud. Observability is deliberately first:
the adapter is built with traces visible from its first model call, not instrumented
afterwards.

Tracing is written against the **OpenTelemetry API only**. Langfuse is a Langfuse-shaped
OTLP exporter injected at composition — no adapter imports the Langfuse SDK, so the same
span-emitting code serves any OTLP backend, and a future domain-side span port can reuse the
attribute vocabulary unchanged.

## Current State Analysis

- `EmbeddingPort` is `async def embed(self, text: str) -> Embedding`
  (`backend/src/application/capture/ports.py:35-36`). Nothing else in the port surface
  concerns embeddings.
- The live implementation is `DeterministicEmbeddingAdapter` — sha512 over the trimmed text,
  32 dimensions scaled into `[-1, 1]`
  (`backend/src/adapters/out/in_memory/capture/embedding.py:8-12`). It cannot fail.
- `VocabularyResolver._best_match` performs exactly one `embed` per resolve
  (`backend/src/application/capture/services/vocabulary.py:37-39`); candidate similarity is
  computed in-process against stored vectors (`backend/src/domain/capture/vocabulary.py:15-27`),
  so the corpus size never multiplies provider calls.
- Those resolves run inside the SSE generator of `GenerateReplyCommand`
  (`backend/src/application/capture/commands/send_message.py:106-120`), served as
  `EventSourceResponse` (`backend/src/adapters/http/capture.py:50`).
- Composition is module-level singletons in `backend/src/adapters/compose.py:135-142`;
  `Settings` is `pydantic-settings` with `extra="forbid"` (`backend/src/config/settings.py`).
- `adapters/out/` holds `in_memory/`, `fsrs/`, `worker/`. There is **no `llm/` package** and
  **no OpenTelemetry configuration anywhere** in the tree.
- `pydantic-ai-slim` resolves to **2.35.3** in `backend/uv.lock` — well past the version that
  introduced embeddings — but the `[openai]` extra is absent, so neither `openai` nor
  `tiktoken` is installed today.
- The embedding contract suite parametrizes over the deterministic adapter only
  (`backend/tests/unit/capture/contracts/test_embedding_contract.py:11-12`).

## Desired End State

`compose.py` builds vocabulary resolution on an OpenRouter-backed embedding adapter by
default, each `embed` emits exactly one OpenTelemetry span carrying Langfuse's observation
attributes, and those spans arrive in a Langfuse Cloud Hobby project. A single smoke script
proves the round trip against the real provider, and both Claude Code and Cursor can query
that Langfuse project over MCP.

Verified by: `uv run python scripts/smoke_embedding.py "TCP handshakes"` printing a
1536-dimension vector (or the configured reduction), the corresponding observation appearing
in the Langfuse UI within seconds, and `/mcp` in Claude Code plus Cursor's MCP panel listing
the Langfuse server as connected.

### Key Discoveries

- **pydantic-ai already has everything.** `Embedder`, `OpenAIEmbeddingModel`,
  `EmbeddingSettings`, and the fake `TestEmbeddingModel` all ship in the installed 2.35.3.
  `OpenRouterProvider` (`pydantic_ai/providers/openrouter.py`) is an accepted provider for
  `OpenAIEmbeddingModel`, so no OpenAI-direct account is needed.
- **The `[openai]` extra is mandatory, not `[openrouter]`.** `pydantic_ai/embeddings/openai.py`
  imports `tiktoken` unconditionally at module import; the `[openrouter]` extra pulls `openai`
  but not `tiktoken`.
- **OpenRouter model ids carry the upstream prefix** — `openai/text-embedding-3-small`, never
  the bare name. `OpenRouterProvider` raises `UserError` on an unprefixed id.
- **Langfuse ingests plain OTLP.** `POST` to `/api/public/otel/v1/traces`, HTTP only (no
  gRPC), Basic auth over `base64(public_key:secret_key)`, plus
  `x-langfuse-ingestion-version: 4` for real-time visibility instead of up-to-10-minute delay.
- **Langfuse renders a span as an observation from attributes alone.**
  `langfuse.observation.type` accepts `"embedding"` outright;
  `langfuse.observation.input` / `.output` (JSON strings), `.model.name`, and
  `.usage_details` fill the detail view. Level and status message are inferred from the OTel
  span status, so `set_status(ERROR)` is enough — no manual level attribute.
- **Langfuse has a first-party hosted MCP server** at
  `https://cloud.langfuse.com/api/public/mcp` (streamable HTTP, Basic auth), exposing prompt
  management *and* observation queries. The `langfuse/mcp-server-langfuse` stdio repo is
  prompt-management-only and is not published to npm — the hosted endpoint makes it moot.
- **The `Embedding` validator already rejects an empty vector** (`EmptyEmbeddingError`,
  code `empty_embedding`, mapped to 422 in `adapters/http/errors.py`), so a malformed
  provider response needs no new adapter guard.
- Storage is entirely in-memory today — no SQLAlchemy repository holds a vector — so moving
  from 32 to 1536 dimensions carries no migration.

## What We're NOT Doing

- **No entry in the embedding contract suite.** Slice S-01's roadmap text promises the
  existing contract suite passes against the new adapter; the author has scoped that out of
  this change in favour of the smoke script alone. `test_embedding_contract.py` keeps its
  single `deterministic` parametrization.
- **No error contract.** Provider faults propagate unchanged. No adapter-owned
  `CoreException` subclass, no `EXCEPTION_STATUS_MAP` entry, no retry, backoff, or fallback.
  A uniform failure taxonomy across all five seams is deferred to a later cross-adapter
  effort where there is enough material to design it.
- **No change to `send_message.py` or the SSE contract**, so a mid-draft embedding failure
  still truncates the stream. That belongs to S-05, which rewrites the streaming path anyway.
- **No blanket OTEL auto-instrumentation** of FastAPI or HTTP clients — every exported span
  is a billable Langfuse observation.
- **No Langfuse scores, datasets, prompt management, or evaluation** — out of scope for the
  whole effort per `context/efforts/llm-adapter/frame.md`.
- **No self-hosted Langfuse**, no Docker Compose additions. Cloud Hobby only.
- **No threshold retuning.** `vocabulary_match_threshold` keeps its current 0.85.
- **No work on the other four seams** (topic extraction, confidence, reply generation, card
  generation) — those are S-05 and S-06.

## Implementation Approach

Four concentric layers, innermost first.

1. **Configuration** carries every provider and telemetry knob, with an explicit
   `embedding_provider` switch defaulting to `openrouter` and overridden to `deterministic`
   in test and CI environments.
2. **`adapters/out/llm/`** holds a vendor-neutral tracing helper and the OpenRouter embedding
   adapter. The helper knows Langfuse's *attribute names* but not its SDK; the adapter knows
   pydantic-ai but not Langfuse. Both depend only on `opentelemetry-api`.
3. **Composition** decides which adapter is built and, separately, where spans are exported.
   `adapters/telemetry.py` is the single place in the tree that knows a Langfuse endpoint and
   credentials exist.
4. **Verification surfaces** — the smoke script and the two MCP configurations — close the
   loop so the author can see a real trace and query it from the editor.

Testing keeps the network out of the suite entirely: `TestEmbeddingModel` swapped in through
`Embedder.override` for the provider side, and OTel's `InMemorySpanExporter` for the span
side.

## Critical Implementation Details

`BatchSpanProcessor` drops buffered spans when a short-lived process exits — the smoke script
must call `force_flush()` before returning, or it will print a vector and silently send
nothing to Langfuse.

`Settings` is `extra="forbid"`, so every new environment variable must be declared as a field
before it can appear in `.env`; an undeclared key fails application startup rather than being
ignored.

---

## Phase 1: Provider and telemetry dependencies, settings, environment

### Overview

Everything the later phases import or read, and nothing else. No behaviour.

### Changes Required:

#### 1. Backend dependencies

**File**: `backend/pyproject.toml`, `backend/uv.lock`

**Intent**: Make the pydantic-ai embeddings path and a plain OTLP exporter importable. The
`[openai]` extra is what pulls `openai` and `tiktoken`, both absent from the lock today.

**Contract**: `dependencies` gains `pydantic-ai-slim[openai]>=2.0.0` (replacing the bare
`pydantic-ai-slim>=0.0.14`, whose lower bound predates embeddings entirely), plus
`opentelemetry-api`, `opentelemetry-sdk`, and `opentelemetry-exporter-otlp-proto-http`.

```bash
cd backend && uv add "pydantic-ai-slim[openai]>=2.0.0" opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

#### 2. Settings

**File**: `backend/src/config/settings.py`

**Intent**: Declare the provider selection, model identity, and telemetry credentials as
typed configuration. The switch is explicit rather than inferred from key presence, so no
environment can start spending tokens by accident.

**Contract**: A `EmbeddingProvider(StrEnum)` with members `DETERMINISTIC` and `OPENROUTER`,
and these `Settings` fields:

```python
embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENROUTER
openrouter_api_key: str | None = None
embedding_model: str = "openai/text-embedding-3-small"
embedding_dimensions: int | None = None
tracing_enabled: bool = True
langfuse_public_key: str | None = None
langfuse_secret_key: str | None = None
langfuse_otlp_endpoint: str = "https://cloud.langfuse.com/api/public/otel/v1/traces"
```

`embedding_dimensions` at `None` means "send no `dimensions` parameter" — the model's own
default, 1536 for `text-embedding-3-small`.

#### 3. Environment template

**File**: `.env.example`

**Intent**: Record every new key with a comment saying what it costs and where it comes from,
including the base64 blob the MCP configurations will reference in Phase 6.

**Contract**: Adds `OPENROUTER_API_KEY`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`,
`EMBEDDING_DIMENSIONS`, `TRACING_ENABLED`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and
`LANGFUSE_MCP_AUTH`. Values are placeholders; `.gitignore` already excludes `.env` while
whitelisting `.env.example`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv sync` resolves with `openai` and `tiktoken` present in `uv.lock`
- `cd backend && uv run python -c "from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel"` exits 0
- `cd backend && uv run pytest` stays green
- `cd backend && uv run ruff check src && uv run basedpyright` report no new findings

#### Manual Verification:
- `cd backend && uv run python -c "from config.settings import Settings; print(Settings().embedding_provider)"` prints `openrouter` with no `.env` override

---

## Phase 2: `adapters/out/llm/` stubs and interfaces

### Overview

Materialize every symbol Phase 3's tests import. Signatures and unimplemented bodies only —
no behaviour.

### Changes Required:

#### 1. Tracing helper

**File**: `backend/src/adapters/out/llm/tracing.py`, `backend/src/adapters/out/llm/__init__.py`

**Intent**: One place that knows how a span must be shaped for Langfuse to read it as an
observation, expressed purely in OpenTelemetry terms so no adapter ever imports a vendor SDK.
Every later LLM adapter, and any future domain-side span port, reuses this vocabulary.

**Contract**: Module-level attribute-name constants and one context manager returning a
recorder:

```python
OBSERVATION_TYPE = "langfuse.observation.type"
OBSERVATION_INPUT = "langfuse.observation.input"
OBSERVATION_OUTPUT = "langfuse.observation.output"
OBSERVATION_MODEL_NAME = "langfuse.observation.model.name"
OBSERVATION_USAGE_DETAILS = "langfuse.observation.usage_details"

class ObservationRecorder:
    def record_output(self, output: object) -> None: ...
    def record_model(self, model_name: str) -> None: ...
    def record_usage(self, usage: Mapping[str, int]) -> None: ...

@contextmanager
def observation(
    name: str, *, observation_type: str, input_value: object
) -> Iterator[ObservationRecorder]: ...
```

The context manager sets the span status to `ERROR` and records the exception on the way out
when the body raises, then re-raises unchanged — Langfuse infers `level` and
`status_message` from span status, so no level attribute is written by hand.

#### 2. OpenRouter embedding adapter

**File**: `backend/src/adapters/out/llm/capture/embedding.py`,
`backend/src/adapters/out/llm/capture/__init__.py`

**Intent**: The `EmbeddingPort` implementation, taking a constructed `Embedder` rather than
building one, so tests can hand it an overridden model and composition owns provider
credentials.

**Contract**:

```python
class OpenRouterEmbeddingAdapter:
    def __init__(
        self, embedder: Embedder, model_name: str, dimensions: int | None = None
    ) -> None: ...

    async def embed(self, text: str) -> Embedding: ...
```

File paths match Phase 3's `**File**` lines. No `EmbeddingPort` signature changes anywhere.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` type-checks the new package with no errors
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run python -c "from adapters.out.llm.capture.embedding import OpenRouterEmbeddingAdapter"` exits 0

#### Manual Verification:
- `cd backend && uv run pytest` — the existing suite is untouched and still green

---

## Phase 3: Adapter behaviour and span emission

### Overview

The adapter embeds through OpenRouter and emits exactly one Langfuse-readable observation per
call. The whole phase is proven without a network call.

### Changes Required:

#### 1. Embedding behaviour

**File**: `backend/src/adapters/out/llm/capture/embedding.py`

**Intent**: Map the port's single string into `Embedder.embed_query` and the returned vector
back into the domain's `Embedding`, honouring the configured model and optional dimension
reduction.

**Contract**: `embed` awaits `self._embedder.embed_query(text)` — passing
`settings=EmbeddingSettings(dimensions=self._dimensions)` only when `dimensions` is not
`None` — and returns `Embedding(values=tuple(result.embeddings[0]))`. A provider exception
propagates unchanged; an empty vector reaches the `Embedding` validator and surfaces as the
existing `EmptyEmbeddingError`.

#### 2. Span emission

**File**: `backend/src/adapters/out/llm/tracing.py`,
`backend/src/adapters/out/llm/capture/embedding.py`

**Intent**: Make each call visible in Langfuse with its input, output shape, model, and token
usage, without the adapter knowing Langfuse exists.

**Contract**: `embed` wraps its provider call in
`observation("embedding", observation_type="embedding", input_value=text)`, records the model
name and the provider's usage details, and records an output summary rather than the raw
vector — 1536 floats in a trace payload are cost without insight. On failure the span carries
`StatusCode.ERROR` and the recorded exception, and the original error still propagates.

#### 3. Tests

**File**: `backend/tests/unit/capture/test_openrouter_embedding_adapter.py`

**Intent**: Pin both halves with no network and no monkeypatching of production internals.

**Contract**: `TestEmbeddingModel(dimensions=...)` installed through `Embedder.override` for
the provider side; a `TracerProvider` with `SimpleSpanProcessor(InMemorySpanExporter())` for
the span side. Cases: vector maps into `Embedding` with the expected dimension; a configured
`embedding_dimensions` reaches the model's `last_settings`; exactly one span is exported per
`embed` and it carries the observation type, input, and model attributes; a raising model
leaves an `ERROR`-status span and the exception reaches the caller unchanged.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_openrouter_embedding_adapter.py -v` passes
- `cd backend && uv run pytest` stays green
- `cd backend && uv run ruff check src tests && uv run basedpyright` report no new findings
- No test in the suite performs a network call — `OPENROUTER_API_KEY` unset still passes

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/capture -v` — read the new test names and confirm they describe adapter behaviour, not the implementation's shape

---

## Phase 4: Telemetry bootstrap and composition wiring

### Overview

Langfuse enters the tree exactly once, as an exporter. The provider switch takes effect.

### Changes Required:

#### 1. Telemetry bootstrap

**File**: `backend/src/adapters/telemetry.py`

**Intent**: Build the global `TracerProvider` and point it at Langfuse over OTLP. This module
is the only one in the tree that names a Langfuse endpoint or credential; nothing imports it
except composition.

**Contract**: `configure_tracing(settings: Settings) -> None` — a no-op when
`tracing_enabled` is false or either Langfuse key is missing. Otherwise it installs a
`TracerProvider` with `BatchSpanProcessor(OTLPSpanExporter(...))` and returns. The exporter
carries two headers, the second being what buys real-time rather than delayed ingestion:

```python
headers = {
    "Authorization": f"Basic {b64encode(f'{public_key}:{secret_key}'.encode()).decode()}",
    "x-langfuse-ingestion-version": "4",
}
```

#### 2. Composition

**File**: `backend/src/adapters/compose.py`

**Intent**: Honour `embedding_provider` and start telemetry before the first adapter is built.

**Contract**: `configure_tracing(_settings)` runs at module import, before `_embedding` is
constructed. `_embedding` comes from a private factory that returns
`DeterministicEmbeddingAdapter()` for `EmbeddingProvider.DETERMINISTIC` and, for
`OPENROUTER`, an `OpenRouterEmbeddingAdapter` around
`Embedder(OpenAIEmbeddingModel(settings.embedding_model, provider=OpenRouterProvider(api_key=...)))`.
`VocabularyResolver`'s construction is unchanged — it receives an `EmbeddingPort` either way.

#### 3. Test and CI environment

**File**: `backend/tests/…` configuration surface (`conftest.py` or `pyproject.toml` env), `.env.example`

**Intent**: Keep the default-on provider from reaching the test suite. Production defaults to
`openrouter`; tests and CI pin `deterministic`.

**Contract**: `EMBEDDING_PROVIDER=deterministic` and `TRACING_ENABLED=false` are set for the
test run, documented alongside the keys in `.env.example`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` passes with no `OPENROUTER_API_KEY` and no Langfuse keys present
- `cd backend && EMBEDDING_PROVIDER=deterministic uv run python -c "import adapters.compose"` exits 0
- `cd backend && uv run ruff check src && uv run basedpyright` report no new findings

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py` starts with `TRACING_ENABLED=false` and no Langfuse keys, emitting no exporter errors
- The same start with real Langfuse keys and `TRACING_ENABLED=true` logs no exporter authentication failure

---

## Phase 5: Smoke script

### Overview

One real call to OpenRouter, one real trace in Langfuse, run by hand. The slice's proof.

### Changes Required:

#### 1. Inline smoke script

**File**: `backend/scripts/smoke_embedding.py`

**Intent**: Prove the whole chain — settings, provider, adapter, span, exporter — in one
invocation the author can rerun whenever a provider or key changes. Deliberately a script,
not a test: it costs money and needs the network.

**Contract**: Reads `Settings`, calls `configure_tracing`, builds the OpenRouter adapter,
awaits one `embed` on a label given as `argv[1]` (defaulting to `"TCP handshakes"`), and
prints the vector dimension, the first few components, and the elapsed time. Ends with
`force_flush()` on the tracer provider before returning — without it a `BatchSpanProcessor`
exits with the span still buffered and Langfuse receives nothing. Prints the Langfuse UI URL
as the last line.

The printed dimension is also the empirical answer to whether OpenRouter honours the
`dimensions` parameter, which its documentation does not state.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check scripts && uv run basedpyright` report no new findings
- `cd backend && EMBEDDING_PROVIDER=deterministic TRACING_ENABLED=false uv run python scripts/smoke_embedding.py "TCP handshakes"` completes offline against the deterministic adapter

#### Manual Verification:
- `cd backend && uv run python scripts/smoke_embedding.py "TCP handshakes"` with real keys prints dimension `1536`
- Re-run with `EMBEDDING_DIMENSIONS=256` — the printed dimension says whether OpenRouter honoured the reduction
- The corresponding observation appears in the Langfuse project within seconds, typed as an embedding, with input text and model name visible

---

## Phase 6: Langfuse MCP for Claude Code and Cursor

### Overview

The author can ask either editor about the traces the previous phase produced.

### Changes Required:

#### 1. Claude Code MCP configuration

**File**: `.mcp.json`

**Intent**: Project-scoped MCP server so a fresh clone picks it up. Langfuse's first-party
hosted server needs no install — it is a remote streamable-HTTP endpoint.

**Contract**:

```json
{
  "mcpServers": {
    "langfuse": {
      "type": "http",
      "url": "https://cloud.langfuse.com/api/public/mcp",
      "headers": { "Authorization": "Basic ${LANGFUSE_MCP_AUTH}" }
    }
  }
}
```

No secret is committed — `${LANGFUSE_MCP_AUTH}` is expanded from the environment and holds
`base64(public_key:secret_key)`.

#### 2. Cursor MCP configuration

**File**: `.cursor/mcp.json`

**Intent**: Same server for the other editor.

**Contract**: The same `mcpServers` object without the `type` field, which Cursor infers from
`url`. Whether Cursor expands `${VAR}` in `headers` is undocumented — the manual step below
settles it, and if expansion does not happen the file falls back to being documentation with
the literal value supplied by the author locally.

#### 3. Documentation

**File**: `.env.example`, `README.md`

**Intent**: Say where `LANGFUSE_MCP_AUTH` comes from — it is the one value a reader cannot
guess.

**Contract**: A README section naming the hosted endpoint, both configuration files, and the
derivation:

```bash
echo -n "pk-lf-xxx:sk-lf-xxx" | base64 -w 0
```

### Success Criteria:

#### Automated Verification:
- `cd /workspaces/weles && python -c "import json; json.load(open('.mcp.json')); json.load(open('.cursor/mcp.json'))"` exits 0
- `git status --porcelain` shows no `.env` staged and neither configuration file contains a literal key

#### Manual Verification:
- `/mcp` in Claude Code lists `langfuse` as connected, and a query for recent observations returns the traces Phase 5 produced
- Cursor's MCP settings panel shows the server connected; record in the plan whether `${VAR}` expansion worked there
- Revoking the environment variable makes both clients fail to connect — proving no key is baked into the repository

---

## Testing Strategy

### Unit Tests

`backend/tests/unit/capture/test_openrouter_embedding_adapter.py` is the whole automated
surface. Provider behaviour comes from pydantic-ai's own `TestEmbeddingModel` through
`Embedder.override`; span behaviour comes from OTel's `InMemorySpanExporter`. No network, no
monkeypatching of production internals, per `context/foundation/testing-conventions.md`.

### Integration Tests

None. The only integration worth having here crosses a paid network boundary, and that is
what the smoke script is for.

### Manual Testing Steps

1. Put real OpenRouter and Langfuse Hobby keys in `.env`.
2. Run the smoke script; confirm the printed dimension.
3. Open the Langfuse project and confirm the observation, its type, input, and model name.
4. Start the backend and drive one capture draft through the TUI; confirm one observation per
   resolved topic and tag label.
5. Query the same project from Claude Code and from Cursor over MCP.

## Performance Considerations

`embed` becomes a network round trip inside the SSE generator of `send_message`, awaited
serially per topic and tag chunk. A draft with one topic and three tags adds four sequential
provider calls to a stream the user is watching. No batching is introduced here —
`EmbeddingPort` takes one string, and widening it to a batch is a port change this slice
explicitly avoids.

Vectors grow from 32 to 1536 floats and cosine similarity is a Python loop over stored
candidates, so per-comparison cost rises 48×. At hobby corpus sizes this is invisible; it
becomes a real question when vocabulary persistence lands.

## Migration Notes

None. No vector is persisted anywhere — every repository is in-memory — so no stored
embedding needs re-encoding. Within a single process the switch must not be flipped at
runtime: mixing 32- and 1536-dimension vectors in one store makes `cosine_similarity` raise
`EmbeddingDimensionMismatchError`. Restarting the process clears the store, which is why the
switch is read once at composition.

## References

- `context/efforts/llm-adapter/frame.md` — FR-08, tracing-only scope, evaluation excluded
- `context/efforts/llm-adapter/roadmap.md` — slice S-01 and what later slices inherit
- `context/changes/llm-adapter-embedding-tracer/research.md` — hobby cost model, OpenRouter embeddings catalogue
- `context/efforts/llm-adapter/research-pydantic-ai.md` — library surface and adapter boundary
- `context/efforts/llm-adapter/research-langfuse.md` — cloud versus self-host, OTLP ingestion
- `context/foundation/rules/layering.md` — `pydantic-ai` confined to adapters
- `context/foundation/rules/contract-testing.md` — one contract per port, cadence by adapter cost
- <https://langfuse.com/integrations/native/opentelemetry> — OTLP endpoint, Basic auth, ingestion version header
- <https://langfuse.com/docs/api-and-data-platform/features/mcp-server> — hosted MCP endpoint
- <https://openrouter.ai/docs/api_reference/embeddings> — embeddings API and provider routing

## Execution State

Execution state lives in `todos.md`, sibling of this file.
