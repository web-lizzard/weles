---
change_id: deployment-manual-deploy
current_phase: 2
next_step: 2.1
next_command: /implement deployment-manual-deploy phase 2
updated: 2026-09-14
---

### Phase 1: Production Backend Image

#### Automated

- [x] 1.1 Dockerignore excludes .env, .venv, tests and mutants — 9d8c236
- [x] 1.2 Dockerfile sets a non-root user and runs uvicorn with one worker — 9d8c236

#### Manual

- [x] 1.3 Image builds locally and contains no /app/.env — 9d8c236
- [x] 1.4 Container started from env vars alone answers /health — 9d8c236

### Phase 2: Deploy Gate

#### Automated

- [ ] 2.1 Actionlint reports no errors on deploy.yml
- [ ] 2.2 workflow_dispatch is the only trigger key

#### Manual

- [ ] 2.3 Check-run names on main head match every ruleset context
- [ ] 2.4 A SHA not on main fails verify naming the ancestry failure
- [ ] 2.5 A main SHA without integration status fails verify naming it
- [ ] 2.6 A main SHA with green checks and integration passes verify
- [ ] 2.7 A push to main starts no deploy run

### Phase 3: Mikrus Host Bootstrap and Runbook

#### Automated

- [ ] 3.1 README has a Hosting on Mikrus section naming no instance
- [ ] 3.2 Both agent guides carry the deploy line and remain identical

#### Manual

- [ ] 3.3 Deploy key logs in on the forwarded SSH port without a password
- [ ] 3.4 Compose plugin v2 is installed and the added disk is mounted at /srv/weles
- [ ] 3.5 Both env files on the VPS are mode 600
- [ ] 3.6 pgvector image pulls on the VPS
- [ ] 3.7 The production environment lists all five DEPLOY_SSH secrets

### Phase 4: Ship to Mikrus

#### Automated

- [ ] 4.1 Actionlint reports no errors on deploy.yml
- [ ] 4.2 Shellcheck reports no findings on remote-deploy.sh
- [ ] 4.3 Deploy job needs verify and uses the production environment

#### Manual

- [ ] 4.4 First gated deploy ends green with postgres and api healthy
- [ ] 4.5 Ports 8000 and 5432 are bound to 127.0.0.1 only
- [ ] 4.6 After migrating over the tunnel the TUI signs in and captures
- [ ] 4.7 Memory snapshot on Mikrus 2.1 is recorded
- [ ] 4.8 A broken deploy ends red with the previous SHA serving
- [ ] 4.9 Deploying an older gated SHA rolls back and keeps at most two image tags
