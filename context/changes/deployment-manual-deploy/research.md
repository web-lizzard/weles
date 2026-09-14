---
date: 2026-09-14T19:45:00+02:00
topic: "Mikrus-hosted database vs Neon, single-box deploy, and ~1s database polling"
topic_slug: null
container_id: deployment-manual-deploy
tags: [research, mikrus, neon, postgres, pgvector, deployment, outbox]
last_updated: 2026-09-14
---

# Research: Mikrus-hosted database vs Neon, single-box deploy, and ~1s database polling

## Research Question

/research deployment-manual-deploy mikrus mozliwosc posiadania bazy danych w mikrusie, jeden depolyment zamiast neon - czy dozwolony odpytywanie bazy co 1s?

## Summary

Mikrus supports PostgreSQL either as a **shared service** (plans 2.1+, panel credentials) or **self-hosted on the VPS** (documented for MariaDB; Postgres via packages or Docker on Docker-capable plans). Replacing Neon with “everything on Mikrus” is **technically plausible** but **not** what deployment S-05 or sibling effort research specifies today: the tracer bullet is **API container on Mikrus + Neon over the internet**. Weles requires **`pgvector`**; Neon documents it on all plans, while Mikrus publishes **no** shared-Postgres extension policy—verify before betting on shared PG.

Mikrus terms do **not** forbid polling a database every second; monitoring, cron, and self-hosted apps are in scope of the product story. Shared databases must stay *“w granicach przyzwoitości”* (~100 MB guidance, no RAM/CPU guarantee). In Weles, the only steady **~1 s** database rhythm is the **outbox worker** (default three lightweight `claim` queries per second when idle), not the TUI or `/health`. Co-located Postgres on the same VPS is usually fine for that load if RAM is sized (often **Mikrus 3.0 / 2 GB** for Docker + Postgres); Neon free tier is mainly challenged by **continuous wake traffic**, not Mikrus ToS.

## Findings

### Mikrus database options

- **Shared PostgreSQL:** Mikrus runs shared DB servers; each user gets one database used *“w granicach przyzwoitości”* with an informal ~100 MB data guideline ([shared databases wiki](https://wiki.mikr.us/wspoldzielone_bazy_danych/)). MySQL, PostgreSQL, and MongoDB appear on 2.x/3.x product pages ([mikr.us](https://mikr.us/)).
- **Credentials:** Panel flow at `https://mikr.us/panel/?a=postgres`; Django wiki example uses host `postgres_server`, port 5432 ([django + PostgreSQL](https://wiki.mikr.us/django_postgresql/)).
- **Self-hosted on VPS:** Wiki documents installing MariaDB on the VPS as an alternative to shared DB ([MySQL/MariaDB configuration](https://wiki.mikr.us/konfiguracja_mysql_mariadb/)). Postgres on the same box (apt or Docker on 2.1+) is the natural pattern for a single-box Weles stack but is **operator-owned** (backups, upgrades, extensions).
- **Shared-service limits:** Regulamin classifies shared DBs as services **without guaranteed RAM/CPU**; exceeding wiki-defined shared limits can lead to warnings and, after seven days, blocking of that shared service ([polityka-prywatnosci / regulamin](https://mikr.us/polityka-prywatnosci/)).
- **Weles `pgvector` gap:** Deployment effort research confirms `pgvector` on Neon ([`research-pg-vector-support.md`](../deployment/research-pg-vector-support.md)). No Mikrus wiki page states whether shared PostgreSQL allows `CREATE EXTENSION vector`. A single-box Weles deploy likely needs **self-hosted** `pgvector/pgvector` (or confirmed extension support via support) plus enough RAM for embeddings indexes.

### Planned architecture vs single-box Mikrus

- Roadmap slice **S-05** describes production as a **container on the Mikrus VPS against Neon**, not Postgres on the VPS ([`roadmap.md`](../../efforts/deployment/roadmap.md)).
- Effort deploy research ends with **“Neon only — no Postgres container on the VPS”** ([`research.md`](../../efforts/deployment/research.md)).
- Moving DB to Mikrus is an **architecture change** (capacity, backups, extension policy), not a configuration tweak inside the current S-05 contract.

### ~1 s database polling in Weles

- **`outbox_poll_interval_seconds`** defaults to **1.0** and drives `OutboxWorker.run_forever` in the API lifespan (`settings.py`, `main.py`, `outbox_worker.py`).
- Each idle tick runs **three** `SqlAlchemyOutboxClaimer.claim` calls (one per outbox handler in `compose.py`)—`SELECT … FOR UPDATE SKIP LOCKED` on the outbox table (`claimer.py`).
- **`GET /health`** returns JSON only; no database probe (`health.py`).
- **TUI** polls due-card count every **15 s** and note list overlay every **3 s** (`app.tsx`, `NoteListOverlay.tsx`); tests may use 1 s intervals but production constants do not.

### Mikrus ToS and 1 Hz polling

- Product positioning includes **monitoring, cron, and automation** ([mikr.us/idea](https://mikr.us/idea)); pricing matrix lists service monitoring on 2.1+ ([mikr.us](https://mikr.us/)).
- **No published rule** caps queries per second or forbids 1 Hz polling on a VPS or shared DB.
- **Forbidden** uses include services that **heavily load the server in a way that hinders other users** or **process huge amounts of data** ([regulamin](https://mikr.us/polityka-prywatnosci/)).
- **CPU** is allocated dynamically; sustained max CPU may be throttled by platform protection ([mikr.us FAQ](https://mikr.us/)).
- **Practical reading:** a single-user API with ~1 s lightweight outbox claims to **localhost Postgres on the VPS** aligns with documented use; the same rate against **shared** Mikrus PostgreSQL is plausible for light queries but subject to neighbor fair use and undocumented connection limits.

### Neon-specific note (if DB stays off Mikrus)

- Continuous API traffic (including outbox polling) can **prevent Neon free-tier scale-to-zero** after five minutes idle ([effort `research.md`](../../efforts/deployment/research.md), [Neon scale to zero](https://neon.com/docs/introduction/scale-to-zero)). That is a **hosting economics** issue, not a Mikrus prohibition. Tuning `OUTBOX_POLL_INTERVAL_SECONDS` is the built-in knob.

## Code References

- `context/efforts/deployment/roadmap.md:114-115` — S-05 tracer: Mikrus container **against Neon**
- `context/efforts/deployment/research.md:96` — end-to-end wiring: Neon only, no Postgres on VPS
- `backend/src/config/settings.py:56` — `outbox_poll_interval_seconds: float = 1.0`
- `backend/src/main.py:24-27` — lifespan starts outbox worker with that interval
- `backend/src/adapters/out/worker/outbox_worker.py:46-56` — sleep loop after `run_once()`
- `backend/src/adapters/compose.py:215-217` — three outbox handlers claimed per tick
- `backend/src/adapters/out/sqlalchemy/shared/outbox/claimer.py:12-37` — `claim` transaction and outbox `SELECT`
- `backend/src/adapters/http/health.py:6-8` — health response without DB
- `tui/src/app.tsx:14` — `DUE_POLL_INTERVAL_MS = 15_000`
- `tui/src/screens/NoteListOverlay.tsx:8` — `NOTES_POLL_INTERVAL_MS = 3000`

## External References

- https://wiki.mikr.us/wspoldzielone_bazy_danych/ — shared MySQL/PostgreSQL; *“w granicach przyzwoitości”*; ~100 MB per user guideline
- https://wiki.mikr.us/django_postgresql/ — shared PostgreSQL via panel; `postgres_server` host example
- https://wiki.mikr.us/konfiguracja_mysql_mariadb/ — self-hosted database on the VPS is supported (MariaDB walkthrough)
- https://mikr.us/idea — hosting for apps, **monitoring**, cron, self-hosting
- https://mikr.us/polityka-prywatnosci/ — shared services lack RAM/CPU guarantee; fair-use enforcement on shared offerings
- https://mikr.us/ — dynamic CPU; throttling under sustained full load; PostgreSQL on 2.x/3.x plans
- https://neon.com/docs/introduction/scale-to-zero — idle compute suspension (relevant when DB remains on Neon)

## Open Questions

- Whether **shared** Mikrus PostgreSQL allows **`pgvector`** (`CREATE EXTENSION vector`) and which Postgres major version runs on `postgres_server`.
- Connection limits and pooling expectations on shared Mikrus PostgreSQL (undocumented publicly).
- If the author adopts **single-box** deploy: backup/restore runbook and whether schema migrations use direct localhost URL only (no pooler analogue).
