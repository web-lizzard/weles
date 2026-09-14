# Manual Deploy to Mikrus — Plan Brief

> Full plan: `plan.md`

## What & Why

The author deploys a chosen `main` commit to their Mikrus VPS, and only a commit whose blocking checks and integration run passed (FR-01, FR-06). This is the first time Weles runs anywhere but a developer machine.

## Starting Point

CI gates pull requests and runs integration on demand, publishing an `integration` status. An S-04 script migrates any direct Postgres URL. There is no production image, no deploy workflow, and nothing on the Mikrus 2.1 VPS.

## Desired End State

The author dispatches `deploy` with a SHA. A commit that is not on `main`, or that lacks green checks or integration, is refused before the VPS is touched. A passing commit's image streams to the VPS, where compose swaps the API next to a local `pgvector` Postgres. An unhealthy API is restored to the previous SHA. Both services listen on `127.0.0.1` only, and the author reaches them through SSH tunnels.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Deploy trigger | `workflow_dispatch` with a SHA input only | Nothing changes because a commit lands on `main` | Frame |
| Gate | SHA on `main`, ruleset contexts green, `integration` status success | Required contexts read from `main.json` cannot drift from the ruleset | Frame / Plan |
| Database | Self-hosted `pgvector/pgvector:pg16` on the VPS, data on an added disk | The 1 s outbox polling would exhaust Neon free CU-hours mid-month, and Mikrus allows the polling | Research / Plan (user) |
| Runtime | `docker compose` stack (`postgres` + `api`) | Two co-located services need network, volume, healthchecks, and start order declared once | Research / Plan (user) |
| Image transport | `docker save \| gzip \| ssh docker load`, no registry | One SSH secret, no registry token on the VPS, image never published | Research / Plan (user) |
| Runtime secrets | Env files only on the VPS (`/srv/weles/*.env`) | App secrets never pass through GitHub; the repo names no instance | Plan (user) |
| Failed deploy | `up --wait`, then restore the SHA in `deployed_sha` and end red | The instance is not left down after a bad deploy | Plan (user) |
| VPS tier | Stay on Mikrus 2.1 (1 GB) | Single-user load, and the upgrade costs time the author lacks; escalate on OOM | Plan (user) |
| Exposure | Bind to `127.0.0.1`, access via SSH tunnels | No public address before S-08 | Frame |
| Migrations | S-04 script unchanged, over `ssh -L 5432` | It accepts any non-pooler Postgres URL | Research / Plan |

## Scope

**In scope:**

- Backend `Dockerfile` and `.dockerignore`
- `deploy.yml` with `verify` and `deploy` jobs
- `deploy/compose.yml` and `deploy/remote-deploy.sh`
- README hosting runbook and the agent-guide line

**Out of scope:**

- Neon, a public address or TLS (S-08), a registry
- Migrate-on-deploy, automated backups
- Error tracking (S-06), diagnostics (S-07)
- A non-root deploy user, a DB-aware health check, a Mikrus 3.0 upgrade

## Architecture / Approach

1. The dispatched workflow's `verify` job checks the SHA against `main`, the ruleset contexts, and `integration`.
2. `deploy` builds `weles-api:<sha>` on the runner and pipes it over SSH (IPv4, port `10000+nr`) into `docker load`.
3. It copies `compose.yml` and `remote-deploy.sh`, then runs the script. The script brings the stack up with the new tag and waits for health, restoring the previous tag on failure.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Production Backend Image | Non-root API image started from env vars alone | A `.env` leaking into the image |
| 2. Deploy Gate | Dispatch-only `verify` that refuses ungated SHAs | Check-run names on `main` differing from ruleset contexts |
| 3. Mikrus Host Bootstrap and Runbook | Prepared VPS and a first-timer runbook | First contact with Mikrus: key login, compose plugin, disk mount |
| 4. Ship to Mikrus | Streamed image, compose switch, auto-restore, rollback | 1 GB RAM without swap; `/health` not proving DB access |

**Prerequisites:** S-01, S-02, S-04 landed; a Mikrus 2.1 VPS with an added disk; Docker available on some machine for Phase 1's manual build.

**Estimated effort:** about a day, most of it Phase 3's manual setup and Phase 4's manual checks.

## Open Risks & Assumptions

- **Memory:** API plus Postgres fit in 1 GB (estimate, not measured). Phase 4 records real figures, and `OOMKilled` or climbing restarts trigger Mikrus 3.0.
- **Key login:** Mikrus accepts key-based SSH on the forwarded port. The wiki documents only passwords.
- **Docker Hub:** pulling `pgvector` may hit rate limits; `docker_proxy` is the documented fallback.
- **Health check:** `/health` does not touch the database, so a green deploy does not prove DB connectivity. The TUI check over the tunnel closes that gap.
- **Frame deviation:** the effort frame and roadmap assume Neon and need an amendment after this change.

## Success Criteria (Summary)

- An ungated SHA is refused, and a gated SHA is deployed with both containers healthy on `127.0.0.1`.
- A broken deploy ends red with the previous SHA serving, and an older gated SHA rolls back.
- The TUI signs in and captures against the hosted instance through an SSH tunnel.
