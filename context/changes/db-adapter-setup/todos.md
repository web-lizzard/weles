---
change_id: db-adapter-setup
current_phase: 1
next_step: 1.3
next_command: /implement db-adapter-setup phase 1
updated: 2026-09-13
---

### Phase 1: Local Postgres with pgvector and MCP access

#### Automated

- [x] 1.1 .mcp.json parses as JSON — 59e7bcb
- [x] 1.2 postgres-mcp launch command resolves with the mcp<2 pin — 59e7bcb

#### Manual

- [ ] 1.3 Rebuild devcontainer and confirm vector extension and TEST_DATABASE_URL
- [ ] 1.4 Query the dev database through the postgres MCP server and see writes refused

### Phase 2: SQLAlchemy adapter and Alembic environment stubs

#### Automated

- [ ] 2.1 basedpyright clean
- [ ] 2.2 ruff check clean over src and tests
- [ ] 2.3 Non-postgres suite passes

### Phase 3: Postgres engine, session source and empty-history migration

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 Postgres integration suite passes
- [ ] 3.2 Full backend suite passes
- [ ] 3.3 basedpyright and ruff clean

#### Manual

- [ ] 3.4 Alembic CLI upgrades the dev database through the adapter alembic.ini
- [ ] 3.5 MCP server sees alembic_version on the dev database
