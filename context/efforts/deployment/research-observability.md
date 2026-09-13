---
date: 2026-09-13T17:10:00+02:00
topic: "Observability options on Mikrus and cloud costs for a hobby deployment"
topic_slug: observability
container_id: deployment
tags: [research, observability, mikrus, sentry, langfuse, uptime, docker]
last_updated: 2026-09-13
---

# Research: Observability options on Mikrus and cloud costs for a hobby deployment

## Research Question

/research deploy --topic observability sprawdź opcje observability na mikrusie, ew sprawdź sentry - jakie koszty chmurowe dla hobbystycznego projektu

## Summary

On a **Mikrus 2.1–3.0** VPS (1–2 GB RAM, LXC, no stable file SWAP), observability RAM is shared with the FastAPI container — **full self-hosted stacks (Loki, SigNoz, self-hosted Sentry) do not fit**. The practical hobby pattern is **SaaS for retention, search, errors, and external uptime**, plus **lightweight on-box tooling** (Dozzle, `docker stats`, Docker log rotation).

**Weles today** already sends **LLM/outbox spans to Langfuse Cloud via OTLP** when tracing is enabled; it has a **shallow `/health`** probe and **stdlib logging** without Sentry, metrics, or structured JSON logs. For production on Mikrus, keep **Langfuse Cloud** for LLM traces (self-hosted Langfuse is not viable on 1–2 GB), add **Sentry Developer ($0)** or **Better Stack free** for unhandled exceptions, and **external uptime** (Better Stack, UptimeRobot, or Checkly free tiers). **Self-hosted Sentry** requires **16 GB RAM** per official docs — not Mikrus-sized; **GlitchTip self-host** documents **512 MB recommended** if a Sentry-compatible stack must live on the VPS.

**Marginal cloud cost for hobby observability:** **$0/month** within free tiers; first paid steps are roughly **Team Sentry ~$26/mo**, **UptimeRobot Solo ~$11/mo**, plus Mikrus **75–130 PLN/year** unchanged.

## Findings

### Mikrus constraints

Mikrus instances are **LXC containers**, not full VMs, and **stable file-based SWAP is not available** ([ograniczenia techniczne](https://wiki.mikr.us/ograniczenia_techniczne_mikrusa/)). Official IPv6/port docs state the **real limit is RAM** — observability processes compete with the API container ([o co chodzi z IPv6](https://wiki.mikr.us/o_co_chodzi_z_ipv6/)). Plan pricing for context: **Mikrus 2.1 — 75 PLN/year (1 GB)**, **Mikrus 3.0 — 130 PLN/year (2 GB)** ([mikr.us](https://mikr.us/)). Host-level status is **status.mikr.us** and panel `stats` — not a substitute for application error tracking or log search.

### Self-hosted vs SaaS on Mikrus

| Approach | RAM on VPS | Hobby cost |
|----------|------------|------------|
| Dozzle (live `docker logs`) | ~50–100 MB cited | $0 |
| Loki + Grafana + Promtail/Alloy | ~1–1.5 GB cited | $0 software; needs 2 GB plan |
| SigNoz (Docker) | **≥4 GB** required | Wrong hardware |
| Self-hosted Sentry | **16 GB RAM + 16 GB swap** min | Wrong hardware |
| GlitchTip self-host | **512 MB recommended** | $0 software |
| SaaS (Sentry, Better Stack, Grafana Cloud, Langfuse Cloud) | SDK/agent only (~0–400 MB) | $0 within free caps |

Heavy stacks on the same box as a Python API risk OOM without swap; **SaaS-first** matches the existing **Neon + GHCR + single API container** deployment sketch in sibling `research.md`.

### Uptime and external checks

External HTTPS checks on `/health` catch DNS, edge TLS, and routing failures that in-container checks miss. Free-tier examples (verify current pages before relying on commercial-use wording):

- **Better Stack:** 10 monitors and heartbeats on the personal free tier ([betterstack.com/pricing](https://betterstack.com/pricing)).
- **UptimeRobot:** 50 monitors, 5-minute interval, framed for hobby/non-profit on the free tier ([uptimerobot.com/pricing](https://uptimerobot.com/pricing/)).
- **Checkly Hobby:** 10 uptime monitors at $0 ([checklyhq.com/pricing](https://www.checklyhq.com/pricing/)).
- **Sentry Developer:** 1 uptime monitor included ([sentry.io/pricing](https://sentry.io/pricing/)).

Self-hosted **Uptime Kuma** on Mikrus costs **~100–400 MiB** with SQLite (avoid embedded MariaDB for memory); external SaaS uptime avoids that RAM entirely.

### Cloud logging, traces, and metrics (hobby tiers)

- **Grafana Cloud Free:** “Always $0”; **10k billable series**, **50 GB ingested each** for logs/traces/profiles, **14-day retention** ([grafana.com/pricing](https://grafana.com/pricing/?pg=prod-cloud)).
- **Better Stack free:** 3 GB logs (3 days), 3 GB traces (3 days), 30 GB metrics, **100k exceptions/month** ([betterstack.com/pricing](https://betterstack.com/pricing)).
- **Axiom Personal:** $0 permanent tier with **500 GB/mo data loading** ([axiom.co/pricing](https://axiom.co/pricing)).
- **Pydantic Logfire Personal:** **10M telemetry records/month**, hard-capped at $0 ([pydantic.dev/logfire/pricing](https://pydantic.dev/logfire/pricing)).

Weles already targets **Langfuse Cloud** for LLM observability, not a second full trace backend unless HTTP spans are unified later via OpenTelemetry.

### Sentry (cloud and self-host)

**Developer (free)** — [sentry.io/pricing](https://sentry.io/pricing/):

- **$0**, **1 user**
- **5k errors/month**, **5M spans**, **50 session replays**, **5 GB logs**, **5 GB application metrics**
- **1 uptime monitor**, **1 cron monitor**, **1 GB attachments**, **20 metric monitors**

**Over quota on Developer:** pay-as-you-go is **not** available; data is **dropped** until upgrade to Team ([Manage Your Error Quota](https://docs.sentry.io/pricing/quotas/manage-event-stream-guide/)).

**Team:** **$26/mo** when billed annually with default pre-paid data; **50k errors** baseline; overages via PAYG ([docs.sentry.io/pricing](https://docs.sentry.io/pricing/)).

**Self-hosted Sentry** minimum: **4 CPU cores**, **16 GB RAM + 16 GB swap**, **20 GB disk** ([develop.sentry.dev/self-hosted](https://develop.sentry.dev/self-hosted/)) — incompatible with Mikrus 1–2 GB.

**Alternatives for hobby error tracking:**

| Product | Free tier (quoted) |
|---------|-------------------|
| Better Stack | 100k exceptions/month ([pricing](https://betterstack.com/pricing)) |
| GlitchTip hosted | 1,000 events/month ([pricing](https://glitchtip.com/pricing)) |
| Highlight.io | 500 monthly sessions ([pricing](https://www.highlight.io/pricing)) |

GlitchTip is **Sentry-SDK–compatible** and documents **512 MB RAM recommended** for self-host ([install](https://glitchtip.com/documentation/install)) — the only Sentry-like stack that plausibly coexists on Mikrus if self-host is mandatory.

### Weles repository — current observability surface

**Implemented:** OpenTelemetry OTLP export with Langfuse Basic Auth and v4 ingestion header (`configure_tracing`, `BatchSpanProcessor`). Tracing is wired at compose import time. LLM adapters and outbox distill handler emit Langfuse-oriented span attributes. Settings and `backend/.env.example` document `TRACING_ENABLED` and Langfuse keys. Pytest disables tracing by default.

**Gaps for Mikrus production:** no `sentry-sdk` integration in application code; no Prometheus or `/metrics`; no global structured JSON logging or request correlation IDs; no FastAPI HTTP auto-instrumentation; no lifespan hook to `force_flush()` OTLP batches on shutdown; `/health` does not verify Postgres/Neon connectivity; deployment effort has no prod observability runbook beyond sibling deploy research (Neon health-ping vs scale-to-zero).

### Recommended stack for Weles on Mikrus (hobby, ~$0/mo marginal)

1. **LLM traces:** Langfuse Cloud (existing OTLP path) — do not self-host Langfuse on Mikrus.
2. **Unhandled errors:** Sentry Developer **or** Better Stack free exceptions — integrate one SDK in the API/worker path.
3. **Uptime:** Better Stack or UptimeRobot free tier against public `GET /health`; tune interval if Neon scale-to-zero is sensitive to frequent probes.
4. **On VPS:** Dozzle + Docker log rotation; optional Netdata on **3.0 only** if host/container charts are wanted (~100–150 MiB vendor claim).
5. **Defer:** Loki, SigNoz, self-hosted Sentry, on-box Uptime Kuma unless upgrading VPS or moving observability off Mikrus.

## Code References

- `backend/src/adapters/telemetry.py:20-39` — OTLP exporter, Langfuse auth headers, `BatchSpanProcessor`
- `backend/src/adapters/compose.py:110-111` — `configure_tracing` at module import
- `backend/src/adapters/out/llm/tracing.py` — Langfuse observation attributes and span helper
- `backend/src/config/settings.py` — `tracing_enabled`, Langfuse keys, OTLP endpoint
- `backend/.env.example` — tracing and Langfuse environment variables
- `backend/src/adapters/http/health.py:6-8` — liveness-only `/health` (no dependency checks)
- `backend/pyproject.toml` — OpenTelemetry SDK and OTLP HTTP exporter dependencies
- `backend/tests/conftest.py` — tracing disabled in tests by default
- `context/efforts/deployment/research.md` — Mikrus deploy topology (Neon, GHCR, wykr.es); Neon health-ping note

## External References

- https://wiki.mikr.us/ograniczenia_techniczne_mikrusa/ — LXC, no stable file SWAP
- https://wiki.mikr.us/o_co_chodzi_z_ipv6/ — RAM as the practical capacity limit
- https://mikr.us/ — Mikrus 2.1/3.0 pricing and RAM
- https://signoz.io/docs/install/docker/ — “At least 4GB of memory allocated to Docker”
- https://www.virtua.cloud/learn/en/tutorials/grafana-loki-log-pipeline-vps — Loki stack ~1–1.5 GB RAM cited
- https://selfhosting.sh/apps/dozzle/ — Dozzle ~50–100 MB RAM cited
- https://develop.sentry.dev/self-hosted/ — self-hosted Sentry 16 GB RAM minimum
- https://sentry.io/pricing/ — Developer free quotas (5k errors, 5M spans, 50 replays, 5 GB logs)
- https://docs.sentry.io/pricing/ — Team $26/mo baseline and PAYG behavior on paid plans
- https://docs.sentry.io/pricing/quotas/manage-event-stream-guide/ — Developer cannot use PAYG; upgrade required
- https://betterstack.com/pricing — free personal tier (monitors, logs, 100k exceptions)
- https://uptimerobot.com/pricing/ — free 50 monitors, 5-minute interval
- https://glitchtip.com/pricing — free 1k events/mo; self-host RAM guidance in install docs
- https://grafana.com/pricing/?pg=prod-cloud — Cloud Free 10k series, 50 GB/mo, 14-day retention
- https://pydantic.dev/logfire/pricing — Personal 10M records/mo hard cap at $0
- https://langfuse.com/self-hosting/deployment/docker-compose.md — self-hosted Langfuse not sized for 1–2 GB VPS (see also `context/efforts/llm-adapter/research-langfuse.md`)

## Open Questions

- Whether `/health` should remain liveness-only or add a separate readiness route that hits Neon without breaking scale-to-zero policy.
- Single vendor vs split: Sentry for errors + Langfuse for LLM traces vs consolidating exceptions into Better Stack while keeping Langfuse.
- Whether to add FastAPI OTEL HTTP instrumentation and correlate logs with `trace_id` without doubling billable Langfuse observations.
