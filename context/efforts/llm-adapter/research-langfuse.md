---
date: 2026-09-11T20:42:00+02:00
topic: "Langfuse observability in the cloud and when self-hosted locally"
topic_slug: langfuse
container_id: llm-adapter
tags: [research, langfuse, observability, llm-adapter, pydantic-ai]
last_updated: 2026-09-11
---

# Research: Langfuse observability in the cloud and when self-hosted locally

## Research Question

potrzebuje informacji o langfuse observability - w chmurze oraz lokalnie

## Summary

Langfuse is an LLM application observability platform: structured tracing of prompts, completions, token usage, latency, tool and retrieval steps, plus sessions, evaluation scores, datasets, and managed prompts. Ingestion is built on **OpenTelemetry**; the official Python and JS SDKs batch traces asynchronously so the hot path stays non-blocking (short-lived processes must call `flush()`).

**Langfuse Cloud** is fully managed multi-tenant SaaS on AWS and ClickHouse Cloud, with isolated regional endpoints (EU, US, Japan, HIPAA). Applications authenticate with project-scoped **public and secret keys** (Basic Auth) and send data via SDKs or OTLP HTTP to `/api/public/otel`. The v4 UI centers on a single **observations** table, trace detail views, session replay, filter search, and human review via annotation queues.

**Self-hosted / local** runs the same application architecture as Cloud: Docker Compose spins up `langfuse-web` (port 3000), `langfuse-worker`, PostgreSQL, ClickHouse, Redis, and MinIO. SDKs differ only by `LANGFUSE_BASE_URL=http://localhost:3000`. The open-core application is MIT-licensed; some enterprise features need `LANGFUSE_EE_LICENSE_KEY`. Compose is aimed at try-out and dev—not HA, horizontal scale, or backups without moving to Helm/Kubernetes or managed infra.

In Weles, Langfuse is not integrated yet. LLM seams exist as application ports and deterministic in-memory adapters; `pydantic-ai-slim` is declared but unused. The natural integration surface is future `adapters/out/llm/` implementations and streaming capture/distill commands.

## Findings

### Product and data model

Langfuse describes application tracing as structured logs per request capturing prompt, model response, token usage, latency, and intermediate steps ([observability overview](https://langfuse.com/docs/observability/overview)). **Observations** are individual steps (LLM calls, tools, retrieval); a **trace** groups observations sharing a `trace_id`. v4 stores conceptually one observations table where each row carries observation-level data and trace-level attributes ([data model](https://langfuse.com/docs/observability/data-model)). **Sessions** optionally group traces (e.g. chat threads) with session replay in the UI ([sessions](https://langfuse.com/docs/observability/features/sessions)). Observation types include `generation`, `span`, `tool`, `agent`, `retriever`, and others ([observation types](https://langfuse.com/docs/observability/features/observation-types)).

Beyond raw traces, Langfuse covers **scores** (manual UI, API, LLM-as-judge), **datasets** (inputs/expected outputs, including cases from production traces), and **prompt management** (central prompts with client-side SDK cache and metrics linked to generations) ([scores overview](https://langfuse.com/docs/scores/overview), [datasets](https://langfuse.com/docs/evaluation/experiments/datasets), [prompt management](https://langfuse.com/docs/prompt-management/overview)).

### Langfuse Cloud

Cloud is documented as fully managed multi-tenant SaaS on AWS and ClickHouse Cloud in isolated regional environments ([security](https://langfuse.com/security)). Regional base URLs include `https://cloud.langfuse.com` (EU), `https://us.cloud.langfuse.com`, `https://jp.cloud.langfuse.com`, and `https://hipaa.cloud.langfuse.com`; accounts and data are not shared across regions ([data regions](https://langfuse.com/security/data-regions)). API keys are created under project settings; REST and SDK auth use Basic Auth with public key as username and secret key as password, project-scoped ([public API](https://langfuse.com/docs/api-and-data-platform/features/public-api), [security FAQ](https://langfuse.com/security/security-faq)).

Getting started env vars for Cloud ([get started](https://langfuse.com/docs/observability/get-started)):

- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` pointing at the chosen region.

Ingestion paths:

- **Python SDK v4** and **JS/TS SDK v5** — OpenTelemetry-based, async, errors caught so they should not break the app ([SDK overview](https://langfuse.com/docs/observability/sdk/overview)).
- **OpenTelemetry OTLP** — `POST` to `/api/public/otel`; Basic Auth; HTTP/JSON or HTTP/protobuf; gRPC not supported yet; header `x-langfuse-ingestion-version: 4` recommended for real-time visibility in v4 ([OpenTelemetry integration](https://langfuse.com/integrations/native/opentelemetry)).
- Legacy ingestion API is deprecated on Cloud with sunset noted for November 2026; OTLP is the supported trace ingestion path ([public API](https://langfuse.com/docs/api-and-data-platform/features/public-api)).

Debugging workflows in Cloud: observations table with default root-observation filter in v4, filter search bar (`level:ERROR`, latency, output text, scores), trace tree/timeline with I/O, sessions, linking prompt versions to generations, annotation queues for expert review ([explore observations v4](https://langfuse.com/faq/all/explore-observations-in-v4), [filter search bar](https://langfuse.com/docs/observability/features/filter-search-bar)).

For teams needing strict infrastructure-level isolation, official docs recommend self-hosting over multi-tenant Cloud ([security FAQ](https://langfuse.com/security/security-faq)).

### Self-hosted and local deployment

Self-hosted v3+ mirrors Cloud infrastructure: web, worker, Postgres, ClickHouse, Redis/Valkey, and S3-compatible blob storage ([self-hosting](https://langfuse.com/self-hosting)). Official local quickstart: clone [langfuse/langfuse](https://github.com/langfuse/langfuse), rotate `# CHANGEME` secrets in `docker-compose.yml`, run `docker compose up`, wait for web container **Ready**, open `http://localhost:3000` ([Docker Compose deployment](https://langfuse.com/self-hosting/deployment/docker-compose.md)).

Compose exposes langfuse-web on **3000**; Postgres, ClickHouse, Redis, and worker are bound to localhost in the default file. Required crypto env includes `NEXTAUTH_URL` (e.g. `http://localhost:3000`), `NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY` (`openssl rand -hex 32`), plus database, ClickHouse, Redis, and S3/MinIO settings on **both** web and worker ([configuration](https://langfuse.com/self-hosting/configuration.md)).

SDK parity with Cloud: same code; only credentials and base URL change — `LANGFUSE_BASE_URL=http://localhost:3000` or constructor `base_url` ([SDK overview](https://langfuse.com/docs/observability/sdk/overview)). OTEL locally: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:3000/api/public/otel` with the same Basic Auth and optional v4 ingestion header ([OpenTelemetry integration](https://langfuse.com/integrations/native/opentelemetry)).

Licensing: MIT for core outside `ee/` paths; enterprise add-ons (RBAC, retention policies, audit logs, etc.) require `LANGFUSE_EE_LICENSE_KEY` ([license key](https://langfuse.com/self-hosting/license-key.md), [GitHub LICENSE](https://github.com/langfuse/langfuse/blob/main/LICENSE)). Compose limitations: no high availability, scaling, or backup story—production self-host prefers Kubernetes Helm or cloud Terraform modules ([Docker Compose deployment](https://langfuse.com/self-hosting/deployment/docker-compose.md)). Sizing: per-component minimums in scaling docs; VM Compose guide recommends about **4 vCPU, 16 GiB RAM, ~100 GiB disk** ([scaling](https://langfuse.com/self-hosting/configuration/scaling.md)). Upgrades: `docker compose up --pull always` or pinned `langfuse/langfuse:4` images; major upgrades have dedicated migration guides ([upgrade](https://langfuse.com/self-hosting/upgrade.md)). OSS telemetry to Langfuse can be disabled with `TELEMETRY_ENABLED=false`; raw traces are not sent in that telemetry ([telemetry](https://langfuse.com/self-hosting/security/telemetry.md)).

Multimodal uploads on default local MinIO may need `LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT=http://localhost:9090` for presigned URLs reachable from the host ([blob storage](https://langfuse.com/self-hosting/deployment/infrastructure/blobstorage.md)).

### Application integration (Python / FastAPI)

There is no first-class FastAPI integration page; official guidance is Python SDK instrumentation inside route handlers (`@observe()`, `start_as_current_observation`, `propagate_attributes` for user/session IDs) ([Python instrumentation](https://langfuse.com/docs/observability/sdk/python/instrumentation)). If using broad OTEL auto-instrumentation, docs warn that filtering out parent spans (e.g. `fastapi`) can orphan child LLM spans as top-level traces, and **every span exported to Langfuse counts as a billable observation** ([existing OTEL setup](https://langfuse.com/faq/all/existing-otel-setup)).

### Weles repository context

No Langfuse, LangChain, or vendor LLM SDK usage exists in application code today. `pydantic-ai-slim` is a dependency but not imported under `backend/src`. Architecture ADRs commit to **pydantic-ai** for LLM adapters with domain isolation from that library. Capture and distill expose ports (`ReplyGenerationPort`, `CardGeneration`, etc.) wired to deterministic in-memory adapters in `compose.py`. Observability today is stdlib `logging` in distill commands and outbox workers only—not OpenTelemetry. The `llm-adapter` effort is open with an unfilled Goal, intended home for LLM adapter work including observability choices.

## Code References

- `backend/pyproject.toml:14` — declares `pydantic-ai-slim>=0.0.14` (transitive OpenTelemetry API only; no app OTel config)
- `backend/src/adapters/compose.py:128-138` — deterministic distill/capture adapters instead of LLM implementations
- `backend/src/application/capture/ports.py:21-32` — LLM-shaped ports including streaming `ReplyGenerationPort`
- `backend/src/application/distill/ports.py:9-10` — `CardGeneration` port for distill LLM calls
- `backend/src/application/capture/commands/send_message.py:76` — streaming reply path relevant for trace spans
- `context/adrs/hexagonal-arch-shape/decision.md` — LLM adapters live outside domain; no pydantic-ai in domain layer
- `context/adrs/backend-stack/decision.md` — pydantic-ai carried for LLM integration
- `context/foundation/rules/layering.md:36` — convention sketch `adapters/out/{…, llm/}` (directory not present yet)
- `context/efforts/llm-adapter/effort.md:2-12` — effort container for LLM adapter work

## External References

- <https://langfuse.com/docs/observability/overview> — defines tracing scope: prompts, responses, tokens, latency, tools, evaluation loop
- <https://langfuse.com/docs/observability/data-model> — observations, traces, sessions, async batch ingestion and `flush()`
- <https://langfuse.com/docs/observability/get-started> — Cloud region base URLs and `LANGFUSE_*` env vars
- <https://langfuse.com/docs/observability/sdk/overview> — Python/JS SDKs, self-host `LANGFUSE_BASE_URL`, `auth_check()`
- <https://langfuse.com/docs/observability/sdk/python/instrumentation> — `@observe()`, generations vs spans, attribute propagation
- <https://langfuse.com/integrations/native/opentelemetry> — OTLP `/api/public/otel`, Basic Auth, v4 ingestion header, no gRPC
- <https://langfuse.com/docs/api-and-data-platform/features/public-api> — project keys; OTLP preferred; legacy ingestion sunset on Cloud
- <https://langfuse.com/security/data-regions> — EU/US/JP/HIPAA endpoints; cross-region isolation and replication limits
- <https://langfuse.com/security/security-faq> — API key model; self-host for infrastructure-level isolation
- <https://langfuse.com/self-hosting> — self-host matches Cloud architecture; optional air-gapped use
- <https://langfuse.com/self-hosting/deployment/docker-compose.md> — clone repo, `docker compose up`, localhost:3000, Compose limits
- <https://langfuse.com/self-hosting/configuration.md> — required env vars on web and worker
- <https://langfuse.com/self-hosting/configuration/scaling.md> — minimum CPU/RAM per component; VM sizing for Compose
- <https://langfuse.com/self-hosting/upgrade.md> — pull-always upgrades and major-version migration guides
- <https://langfuse.com/self-hosting/license-key.md> — MIT core vs enterprise license key
- <https://github.com/langfuse/langfuse/blob/main/docker-compose.yml> — six-service stack and `# CHANGEME` secrets
- <https://langfuse.com/faq/all/existing-otel-setup> — billable observations per span; FastAPI span filtering pitfalls

## Open Questions

- Which deployment mode fits Weles phases: Cloud free tier for dev, self-hosted Compose in devcontainer, or Cloud EU for production data residency?
- Should observability wrap pydantic-ai/agent instrumentation only, or instrument at hexagonal adapter boundaries to keep domain free of Langfuse imports?
- Policy for OTEL auto-instrumentation volume (FastAPI/HTTP) given per-observation billing on Cloud?
- Whether to add Langfuse Compose as optional infra alongside existing backend dev setup and wire `LANGFUSE_INIT_*` for headless project keys locally.
