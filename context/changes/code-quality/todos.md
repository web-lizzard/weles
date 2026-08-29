---
change_id: code-quality
current_phase: 5
next_step: 5.1
next_command: /implement code-quality phase 5
updated: 2026-08-29
---

### Phase 1: Backend — Ruff config and cleanup

#### Automated

- [x] 1.1 `cd backend && uv run ruff check .` exits 0 — b1e49d5
- [x] 1.2 `cd backend && uv run ruff format --check .` exits 0 — b1e49d5

### Phase 2: Backend — Replace mypy with basedpyright, config and cleanup

#### Automated

- [x] 2.1 `cd backend && uv run basedpyright` exits 0 — 5a8e381

### Phase 3: Backend — pre-commit wiring

#### Automated

- [x] 3.1 `pre-commit run ruff-check --all-files` exits 0 — 02b7b72
- [x] 3.2 `pre-commit run ruff-format --all-files` exits 0 — 02b7b72
- [x] 3.3 `pre-commit run basedpyright --all-files` exits 0 — 02b7b72

#### Manual

- [x] 3.4 Stage a deliberately broken file under `backend/`, confirm `git commit` is rejected, then discard the staged change

### Phase 4: TUI — Biome config and cleanup

#### Automated

- [x] 4.1 `cd tui && pnpm install` completes (new dependency) — 61eec32
- [x] 4.2 `cd tui && pnpm exec biome check .` exits 0 — 61eec32

### Phase 5: TUI — pre-commit wiring

#### Automated

- [ ] 5.1 `pre-commit run biome-check --all-files` exits 0

#### Manual

- [ ] 5.2 Stage a deliberately broken file under `tui/`, confirm `git commit` is rejected, then discard the staged change
