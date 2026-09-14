---
effort_id: deployment
title: Deployment
status: active
created: 2026-09-12
updated: 2026-09-14
archived_at: null
---

## Goal

Weles runs only on a developer machine today: nothing publishes the TUI, no CI verifies a change, and no hosted instance exists that the author or the certification reviewer could use. This effort puts the author's instance into production on a Mikrus VPS, backed by Neon, and the author and the reviewer use it through a TUI that anyone can install without credentials. A change reaches `main` only through a pull request that passed the unit and BDD suites. The hosted instance changes only when the author deliberately deploys a chosen `main` commit that also passed the Postgres integration suite. Unhandled errors surface in error tracking without exposing anything people wrote, and an agent can diagnose a broken instance read-only and recommend next steps. The instance's address stays hard to discover, and it goes public only once `auth-flow` separates each person's data.
