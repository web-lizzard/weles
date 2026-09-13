---
effort_id: db-adapter
title: Db adapter
status: done
created: 2026-09-12
updated: 2026-09-14
archived_at: 2026-09-13T22:05:20Z
---

## Goal

Make Weles's state durable. Capture, distill, remember and the shared outbox all run on in-memory adapters today, so everything is lost when the daemon restarts. This effort moves each of them onto PostgreSQL through SQLAlchemy async adapters, one surface at a time (outbox, then capture, then distill, then remember), with an Alembic revision per surface. The daemon switches over once all four are delivered. It succeeds when four things hold: every surface survives a restart; a command's state change and its outbox envelopes commit together; the outbox carries work across modules end to end on Postgres, proven by contract and integration tests; and the author can query local rows through a Postgres MCP server.
