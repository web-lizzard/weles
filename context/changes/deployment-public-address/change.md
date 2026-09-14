---
change_id: deployment-public-address
title: The author and the reviewer reach the hosted instance at a hard-to-discover public address
status: planned
created: 2026-09-14
updated: 2026-09-14
archived_at: null
effort_id: deployment
slice_ref: S-08
---

## Notes

<!-- Materialized from effort `deployment`, slice S-08. Run /plan deployment-public-address to write the plan. -->

Materialized early, on the author's explicit request, while prerequisite S-05 (`deployment-manual-deploy`) is still in progress. The roadmap's `Prerequisites: S-05` line is left unchanged on purpose.

- **Why early:** time is short. Directional research and the plan for the address mechanism need no running instance, so they start now in parallel with S-05.
- **Delivery order stands:** implementation and verification of this change start only after S-05 is done. They need the deployed instance on Mikrus, currently bound to `127.0.0.1` and reached through SSH tunnels.
- **auth-flow gate:** the slice's outside gate is already met. auth-flow S-01, S-04, and S-05 are `done` in `context/efforts/auth-flow/roadmap.md`.
- **Carried assumption from S-05's plan:** the database is a self-hosted `pgvector` container on the VPS, not Neon. The API listens on `127.0.0.1:8000` behind no proxy. See `context/changes/deployment-manual-deploy/plan.md`.
