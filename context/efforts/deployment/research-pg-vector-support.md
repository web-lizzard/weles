---
date: 2026-09-13T18:15:00+02:00
topic: "Whether Neon Postgres supports the pgvector extension for production deployment"
topic_slug: pg-vector-support
container_id: deployment
tags: [research, neon, pgvector, postgres, deployment]
last_updated: 2026-09-13
---

# Research: Whether Neon Postgres supports the pgvector extension for production deployment

## Research Question

sprawdź, czy neon wspiera

## Summary

**Yes.** Neon supports the **`pgvector`** extension on **every plan**, including the free tier, with no separate add-on. Enable it per database with `CREATE EXTENSION IF NOT EXISTS vector;`. Supported versions are listed on Neon’s Postgres extensions page (currently **0.8.0–0.8.1** depending on Postgres major version). HNSW and IVFFlat indexes, standard distance operators, and types such as `vector`, `halfvec`, `bit`, and `sparsevec` are documented for Neon. For Weles, **1536-dimensional** embeddings (e.g. OpenAI `text-embedding-3-small`) fit within Neon’s **2000-dimension** limit for indexed `vector` columns. Operational limits (free-tier storage, compute hours, scale-to-zero, pooler vs direct host for migrations) are unchanged from sibling deploy research—they constrain hosting cost and ops, not whether pgvector is available.

## Findings

### Neon platform

- **`pgvector` on all plans:** Neon documents that pgvector is available on every Neon plan with no add-on or paid tier required; the extension is installed **per database**, so run `CREATE EXTENSION` in each database that will store vectors.
- **Enablement:** `CREATE EXTENSION IF NOT EXISTS vector;` from the SQL Editor, psql, or any Postgres client ([pgvector docs](https://neon.com/docs/extensions/pgvector), [FAQ](https://neon.com/faqs/enable-pgvector-extension)).
- **Versions:** The [supported extensions table](https://neon.com/docs/extensions/pg-extensions) lists `pgvector` with install via `CREATE EXTENSION vector;` and version cells per Postgres major (e.g. 0.8.0 on PG 14–17, 0.8.1 on PG 18). Neon allows installing **one version back** from the latest supported version if needed.
- **Capabilities:** Exact and approximate nearest-neighbor search; HNSW and IVFFlat indexes; L2, inner product, cosine, L1, Hamming, and Jaccard distance; `vector` (up to 2000 dimensions for HNSW/IVFFlat), `halfvec`, `bit`, `sparsevec` ([pgvector extension page](https://neon.com/docs/extensions/pgvector)).

### Weles repository alignment

- Deployment effort already assumed Neon + pgvector in the main deploy research summary; this topic file confirms that assumption against current Neon docs.
- Backend ADR defers exercising `pgvector` column types until Postgres adapters beyond Notion are built; deployment choice of Neon does not block future embedding storage in Postgres.
- Local dev uses `pgvector/pgvector:pg16` in the devcontainer; integration tests assert the `vector` extension is available on the dev Postgres instance.
- Planned embedding dimension (1536) is within Neon’s documented `vector` index dimension limits.

### Operations (pgvector-adjacent)

- **Migrations / DDL** (including `CREATE EXTENSION` and index builds): use a **direct** (non-pooler) connection; the API should use the **`-pooler`** hostname in transaction mode for steady traffic—same split as in `context/efforts/deployment/research.md`.
- **Free tier:** pgvector is supported, but **0.5 GB storage** and monthly compute caps still apply; large embedding tables need capacity planning, not a different vendor for the extension itself.

## Code References

- `context/efforts/deployment/research.md:74` — prior deploy research note: pgvector on all Neon plans
- `context/efforts/deployment/research.md:140-141` — external links to Neon pricing and pgvector docs
- `context/adrs/backend-stack/decision.md:25` — pgvector/SQL path untested until outbox/tags/flashcards adapters
- `context/efforts/db-adapter/research-sql-alchemy.md` — planned pgvector columns for embeddings
- `backend/tests/integration/postgres/test_database_tooling.py:58-68` — dev Postgres exposes `vector` in `pg_available_extensions`
- `backend/.env.example:31` — optional embedding dimensions; default model size 1536 for text-embedding-3-small

## External References

- https://neon.com/docs/extensions/pgvector — “`pgvector` is available on every Neon plan with no add-on or paid tier required”; enable with `CREATE EXTENSION IF NOT EXISTS vector;`; HNSW/IVFFlat and vector types
- https://neon.com/faqs/enable-pgvector-extension — FAQ: single-statement install; per-database scope; HNSW as production index default
- https://neon.com/docs/extensions/pg-extensions — supported `pgvector` versions per Postgres major; `CREATE EXTENSION vector;`
- https://neon.com/docs/connect/connection-pooling — pooler vs direct connections (migrations and extension DDL on direct)

## Open Questions

- Whether Neon **free-tier 0.5 GB** storage is sufficient for expected embedding row count and index overhead at personal scale, or a paid Launch tier is needed for headroom only (not for pgvector availability).
- Whether Alembic migrations will use `CREATE EXTENSION vector` in-repo vs manual one-time enablement in the Neon console for each environment database.
