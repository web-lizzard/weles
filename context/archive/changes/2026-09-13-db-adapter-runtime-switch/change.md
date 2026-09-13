---
change_id: db-adapter-runtime-switch
title: The daemon runs on Postgres and its state survives a restart
status: archived
created: 2026-09-13
updated: 2026-09-13
archived_at: 2026-09-13T22:01:58Z
effort_id: db-adapter
slice_ref: S-06
---

## Notes

Closed without a materialized plan or `/implement` loop. Runtime switch landed directly in
`backend/src/adapters/compose.py` (SQLAlchemy UoWs, outbox claimer/query, distill query
adapters, remember catalog/locator and query readers). See commit `68b2773` and follow-ups on
`main`.
