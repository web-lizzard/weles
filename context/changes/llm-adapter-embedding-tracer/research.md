---
date: 2026-09-11T22:02:00+02:00
topic: "Hobby-project cost model for S-01 embedding and Langfuse tracing"
topic_slug: null
container_id: llm-adapter-embedding-tracer
tags: [research, llm-adapter, embedding, langfuse, hobby-cost, vocabulary]
last_updated: 2026-09-11
last_updated_note: "OpenRouter embedding API, model catalog, and pydantic-ai routing"
---

# Research: Hobby-project cost model for S-01 embedding and Langfuse tracing

## Research Question

uzupełnij research z effortu o koszta dla projektu hobbystycznego

## Summary

For a **hobby project** (solo author, manual verification, CI still on in-memory adapters), **S-01** model spend is negligible and **Langfuse Cloud Hobby ($0)** is sufficient for a long time if tracing stays **narrow**—no blanket FastAPI OTEL auto-instrumentation and no evaluation scores (out of scope per `context/efforts/llm-adapter/frame.md`). The meaningful budget risk is **later slices S-05/S-06** (chat completions), not vocabulary embeddings.

**Embeddings:** OpenAI `text-embedding-3-small` bills **$0.02 per 1M input tokens** (batch **$0.01 / 1M** when used). Each `VocabularyResolver.resolve_topic` / `resolve_tag` performs exactly one `EmbeddingPort.embed` per label. Draft replies invoke those resolves from streaming draft chunks, so cost scales with **topic + tag labels per agent reply**, not with candidate corpus size (similarity runs in-process over stored embeddings). At ~5–15 tokens per short label, even **~3,000 embed calls/month** is on the order of **tens of cents per year**, not dollars.

**Langfuse (tracing only):** Hobby includes **50,000 billable units/month**, **30-day retention**, **2 users**, **$0**, no credit card; usage beyond the cap **stops ingestion** (no overage on Hobby). A unit is **traces + observations + scores** combined. Instrumenting each embed as **one observation** (no scores) yields ~**1 unit per API embed**—roughly **5k units/month** at 5k embeds, well under the Hobby cap. Self-hosted OSS is **MIT, unlimited units**; hobby cost is **local Docker RAM/disk**, not a standing cloud bill unless Langfuse runs 24/7 on a VPS.

**CI:** Contract suites keep using `DeterministicEmbeddingAdapter`; no provider charges on every push.

**Later effort slices (orientation only):** Live capture/distill add chat tokens (orders of magnitude above embeddings) and more Langfuse units per user message when each LLM step is a separate observation. Hobby chat with a small model (e.g. `gpt-4o-mini` at published **$0.15 / $0.60 per 1M input/output tokens**) remains affordable at tens–low hundreds of sessions per month if usage is manual, but Langfuse unit math should be watched once multi-step agent tracing lands.

Sibling effort research (`research-current-context`, `research-pydantic-ai`, `research-langfuse`) covers ports, library surface, and deployment; this document adds **quantified hobby economics** for slice S-01 and a forward-looking envelope for the effort.

## Findings

### How embedding spend is generated in Weles

- `VocabularyResolver._best_match` calls `await self._embedding.embed(label.value)` once per resolve (`backend/src/application/capture/services/vocabulary.py:37-39`).
- `GenerateReplyCommand` calls `resolve_topic` on each `DraftTopicChunk` and `resolve_tag` on each `DraftTagChunk` while streaming (`backend/src/application/capture/commands/send_message.py:106-120`).
- Candidate search does **not** call the provider again—it compares the new embedding to stored topic/tag embeddings via cosine similarity in the domain (`backend/src/domain/capture/vocabulary.py:15-27`).
- Production wiring today uses `DeterministicEmbeddingAdapter` (`backend/src/adapters/compose.py:138-140`); real adapter swap is the S-01 target without port signature changes (`context/efforts/llm-adapter/roadmap.md` slice S-01).

### Provider and library pricing (embeddings)

- OpenAI lists **`text-embedding-3-small` at $0.02 / 1M tokens** (input-only billing for embeddings); **`text-embedding-3-large` at $0.13 / 1M** for higher quality at ~6.5× cost ([OpenAI model page](https://developers.openai.com/api/docs/models/text-embedding-3-small)).
- Pydantic AI exposes the same models via **`Embedder('openai:text-embedding-3-small')`** / `OpenAIEmbeddingModel` with optional **`EmbeddingSettings(dimensions=…)`** Matryoshka reduction ([embeddings guide](https://pydantic.dev/docs/ai/guides/embeddings/)); library license is MIT—no separate per-call fee ([effort `research-pydantic-ai.md`](../../efforts/llm-adapter/research-pydantic-ai.md)).
- New OpenAI accounts commonly receive **starter API credits** (often on the order of a few dollars)—enough for **hundreds of millions of embedding tokens** during early integration, though credit policies change and should be verified in the OpenAI dashboard at signup.

### Worked hobby scenarios (embedding API only)

Assumptions: **10 tokens per label** (conservative mid-range for short topic/tag strings), **`text-embedding-3-small` standard (not batch)**.

| Pattern | Embed calls / month | Tokens / month | Approx. API cost / month |
| --- | ---: | ---: | ---: |
| Light manual testing | 200 | 2,000 | < $0.001 |
| Regular dev (500 draft replies × 1 topic + 3 tags) | 2,000 | 20,000 | ~$0.0004 |
| Heavy month (2,000 replies × 6 labels) | 12,000 | 120,000 | ~$0.0024 |
| Stress re-embed / experiments | 50,000 | 500,000 | ~$0.01 |

Even the stress row is **~$0.12/year** at published list price—embedding is not the hobby budget bottleneck.

### Langfuse Cloud (tracing-only scope)

- **Hobby:** **50k units/month included**, **$0**, **30-day data access**, **2 users**, community support; positioned for hobby/POC ([pricing](https://langfuse.com/pricing)).
- **Billable unit definition:** `Units = Traces + Observations + Scores` ([billable units](https://langfuse.com/docs/administration/billable-units)).
- **Hobby hard cap:** third-party summaries and pricing page align that **overage is not billed on Hobby—ingestion stops** when the cap is hit (contrast **Core ~$29/mo** with overage at **~$8 / 100k units** beyond included volume).
- **Instrumentation guidance for S-01:** emit **one observation per successful `embed()`** (optionally nest under a per-request trace when HTTP context exists). Avoid enabling broad OTEL auto-instrumentation on FastAPI/HTTP—effort research notes **each exported span counts as a billable observation** ([Langfuse OTEL FAQ](https://langfuse.com/faq/all/existing-otel-setup), summarized in `context/efforts/llm-adapter/research-langfuse.md`).
- **Exclude scores and Langfuse eval features**—explicitly out of scope for the effort (`context/efforts/llm-adapter/frame.md`).

| Tracing pattern | Units per embed call | 5k embeds / month | 25k embeds / month |
| --- | ---: | ---: | ---: |
| 1 observation only | 1 | 5,000 | 25,000 |
| 1 trace + 1 observation | 2 | 10,000 | 50,000 (at Hobby cap) |

At hobby embedding volumes, **observation-only** or **trace+observation** both usually stay within **50k units** unless embed call volume or multi-layer tracing grows sharply before chat slices add many LLM observations per message.

### Self-hosted Langfuse vs Cloud for a hobbyist

- **OSS self-host:** **no usage-based license fee**, unlimited units ([self-hosted pricing](https://langfuse.com/pricing-self-host)); same tracing features as Cloud core for MIT paths (effort `research-langfuse.md`).
- **Real costs:** engineer time + **local machine resources** (official Compose sizing ~**4 vCPU, 16 GiB RAM, ~100 GiB disk** in effort research)—acceptable on a dev laptop that already runs Weles; **not** comparable to managed observability stacks quoted at **hundreds of USD/month** for always-on cloud ClickHouse unless the hobbyist chooses that ops burden.
- **Cloud Hobby** wins when the author wants **zero infra** and accepts **30-day retention** and the **50k unit cap**.

### CI, contracts, and non-goals

- Hexagonal ADR: **in-memory adapters on every CI run**; LLM-backed adapters on a **non-blocking** cadence (`context/adrs/hexagonal-arch-shape/decision.md`)—hobby API keys are not spent on each push.
- Evaluation (datasets, LLM-as-judge, Langfuse scores) is **out of effort scope**—no budget line for eval units or judge model calls in this frame.

### Forward-looking hobby envelope (S-05 / S-06, not S-01)

- **Chat models** dominate spend once capture/distill go live: e.g. **`gpt-4o-mini`** published at **$0.15 / $1M input** and **$0.60 / $1M output** ([OpenAI model page](https://developers.openai.com/api/docs/models/gpt-4o-mini)). A single long capture turn (illustrative **15k input + 4k output tokens** across topic/confidence/reply) is ~**$0.004–0.005**—**100 such turns/month ~ $0.40–0.50** before embeddings or tracing.
- **Langfuse units** for multi-step capture (trace + several generations/spans per user message) often land in **~5–15 units per message** in industry rule-of-thumb write-ups; **200 messages/day in dev** can approach **tens of thousands of units/month**—still often Hobby-safe, but closer to the cap than embedding-only tracing. **Core** becomes relevant when retention >30 days or sustained production traffic exceeds Hobby limits.

## Code References

- `backend/src/application/capture/services/vocabulary.py:37-39` — one provider embed per resolve
- `backend/src/application/capture/commands/send_message.py:106-120` — topic/tag resolves during draft streaming
- `backend/src/application/capture/ports.py:35-36` — `EmbeddingPort` protocol
- `backend/src/adapters/compose.py:138-142` — deterministic embedding + `VocabularyResolver` wiring
- `backend/src/adapters/out/in_memory/capture/embedding.py:8-12` — CI-safe stand-in (no API cost)
- `backend/src/domain/capture/vocabulary.py:15-27` — in-process similarity; no extra embed calls for candidates
- `context/efforts/llm-adapter/frame.md:67-67` — Langfuse tracing only; evaluation out of scope
- `context/efforts/llm-adapter/roadmap.md:34-49` — S-01 outcome and inheritance of llm + tracing wiring

## External References

- <https://developers.openai.com/api/docs/models/text-embedding-3-small> — `$0.02` per 1M tokens (standard embedding pricing)
- <https://pydantic.dev/docs/ai/guides/embeddings/> — `Embedder('openai:text-embedding-3-small')`, dimension settings, OpenAI-compatible providers
- <https://developers.openai.com/api/docs/models/gpt-4o-mini> — illustrative hobby chat pricing for later slices
- <https://langfuse.com/pricing> — Hobby 50k units/month, $0, 30-day retention, 2 users; Core/Pro overage tiers
- <https://langfuse.com/docs/administration/billable-units> — `Units = Traces + Observations + Scores`
- <https://langfuse.com/pricing-self-host> — MIT self-host, no usage-based OSS billing
- <https://langfuse.com/faq/all/existing-otel-setup> — per-span billing; caution on FastAPI OTEL volume

## Open Questions

- Default settings: OpenAI direct vs OpenRouter/OpenAI-compatible local endpoint (same unit economics if list prices differ per provider)?
- Langfuse shape for S-01: single observation per `embed()` vs one trace wrapping vocabulary resolve for a whole draft reply?
- Hobby deployment default: **Langfuse Cloud EU Hobby** vs **local Docker Compose** alongside the backend dev environment?

## Follow-up Research 2026-09-11

### Research Question

czy OpenRouter oferuje embeddingowe modele?

### Summary

**Yes.** OpenRouter exposes a dedicated **Embeddings API** (`POST /api/v1/embeddings`) and a separate catalog endpoint (`GET /api/v1/embeddings/models`). Models are listed with `output_modalities` including **`embeddings`**; the public collection includes OpenAI `text-embedding-3-small` / `text-embedding-3-large`, Qwen3 embedding variants, Google Gemini Embedding (including multimodal Gemini Embedding 2), Voyage, Mistral Embed, Perplexity embed models, and others—not only OpenAI reroutes.

For Weles S-01, **`openai/text-embedding-3-small`** on OpenRouter is the natural OpenRouter pick: docs example pricing shows **`prompt: "0.00000002"`** per token (**$0.02 / 1M**), aligned with OpenAI list pricing for the same model id. Hobby spend stays in the sub-cent range described in the main document; the main difference vs OpenAI direct is **one API key and one billing surface** for later chat slices on OpenRouter, plus optional **`provider`** routing (order, fallbacks, data-collection policy).

Pydantic AI can reach OpenRouter embeddings via **`OpenAIEmbeddingModel` + `OpenRouterProvider`** (OpenAI-compatible `/embeddings` on `https://openrouter.ai/api/v1`), matching how chat models already use OpenRouter in pydantic-ai docs—model string uses OpenRouter slugs (e.g. `text-embedding-3-small` with OpenRouter provider, or verify exact id `openai/text-embedding-3-small` in the list API). Official pydantic-ai embedding docs still emphasize OpenAI/Azure/Ollama examples; OpenRouter is documented for chat and fits the **OpenAI-compatible provider** pattern for embeddings.

### Findings

#### OpenRouter product surface

- Unified embeddings router: POST **`https://openrouter.ai/api/v1/embeddings`** with `model`, `input`, optional `dimensions`, `input_type`, `provider`, and multimodal `input` blocks for image-capable models ([embeddings overview](https://openrouter.ai/docs/api_reference/embeddings)).
- Model discovery: **`GET /api/v1/embeddings/models`** (paginated `limit` up to 1000) returns embedding-only catalog entries; general **`GET /api/v1/models?output_modalities=embeddings`** also filters embedding-capable models ([list embeddings models](https://openrouter.ai/docs/api/api-reference/embeddings/list-embeddings-models), [models guide](https://openrouter.ai/docs/guides/overview/models)).
- Response includes OpenAI-style **`usage.prompt_tokens`** and OpenRouter **`usage.cost`** in credits ([create embeddings API](https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings)).
- **Provider routing** on embedding requests mirrors chat: `provider.order`, `allow_fallbacks`, `data_collection` ([embeddings guide — provider routing](https://openrouter.ai/docs/api_reference/embeddings)).

#### Catalog snapshot (illustrative, not exhaustive)

OpenRouter’s **Text Embedding Models** collection ranks by weekly usage; documented examples include:

| OpenRouter model id (examples) | Notes |
| --- | --- |
| `openai/text-embedding-3-small` | Default cheap path; 8192 context in API example |
| `openai/text-embedding-3-large` | Higher quality, higher $/token on OpenRouter listing |
| `qwen/qwen3-embedding-8b` (and smaller Qwen3 embedding variants) | Non-OpenAI alternative |
| Google Gemini Embedding / Gemini Embedding 2 | Text and multimodal (text+image) embeddings |
| `voyage-*`, Mistral Embed, Perplexity `pplx-embed-*` | Third-party embedding families |

Browse live prices and dimensions: <https://openrouter.ai/models?fmt=cards&output_modalities=embeddings> and <https://openrouter.ai/collections/embedding-models>.

#### Implications for llm-adapter-embedding-tracer

- **Open question partial answer:** OpenRouter is a viable default provider for hobby if the author already plans OpenRouter for S-05/S-06—embedding labels through the same key avoids a second vendor for S-01.
- **Quality/dimension contract:** Weles stores whatever vector `EmbeddingPort` returns; switching from deterministic 32-dim hashes to **1536-dim** (default for `text-embedding-3-small`) is an adapter concern—the embedding contract requires stable nonzero dimension, not a fixed size (`backend/tests/unit/capture/contracts/test_embedding_contract.py`).
- **Multimodal OpenRouter embeddings** are irrelevant to S-01 (`Label` text only in `VocabularyResolver`).

### External References

- <https://openrouter.ai/docs/api_reference/embeddings> — embeddings API, batch input, multimodal input, semantic search example
- <https://openrouter.ai/docs/api/api-reference/embeddings/list-embeddings-models> — `GET /embeddings/models`; example `openai/text-embedding-3-small` with `prompt: "0.00000002"`
- <https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings> — `POST /embeddings`, usage.cost, dimensions parameter
- <https://openrouter.ai/collections/embedding-models> — curated embedding model collection
- <https://openrouter.ai/models?fmt=cards&output_modalities=embeddings> — filter UI for embedding output modality
- <https://pydantic.dev/docs/ai/guides/embeddings/#openai-compatible-providers> — `OpenAIEmbeddingModel` with custom `OpenAIProvider` base URL (same pattern as OpenRouter)
- <https://ai.pydantic.dev/models/openrouter/> — OpenRouter chat integration via `OpenRouterProvider` (shared provider stack with embeddings)
