---
change_id: tui-bootstrap
current_phase: 4
next_step:
next_command: /archive tui-bootstrap
updated: 2026-08-28
---

### Phase 1: Devcontainer — enable pnpm + workspace root

#### Manual

- [x] 1.1 Rebuild the devcontainer — f0ff634
- [x] 1.2 `pnpm --version` succeeds inside the rebuilt container — f0ff634
- [x] 1.3 `ordo status` still succeeds — f0ff634

### Phase 2: TUI project scaffolding

#### Automated

- [x] 2.1 `pnpm install` (repo root) exits 0 — 33f5cc7
- [x] 2.2 `pnpm --filter tui typecheck` exits 0 — 33f5cc7
- [x] 2.3 `pnpm --filter tui build` exits 0 — 33f5cc7

### Phase 3: Bootstrap contract — stubs

#### Automated

- [x] 3.1 `pnpm --filter tui typecheck` exits 0 — a3a440c
- [x] 3.2 `pnpm --filter tui build` exits 0 — a3a440c

### Phase 4: Bootstrap contract — behavior

#### Tests

- [x] tests generated — 77706a2

#### Automated

- [x] 4.1 `pnpm --filter tui test` passes (App renders `"Weles TUI — bootstrap OK"`) — 353c17d

#### Manual

- [x] 4.2 `pnpm build` (in `tui/`) then `node dist/cli.js` prints `Weles TUI — bootstrap OK`

#### Triage

- [x] 4.3 R1-F1 `pnpm --filter tui typecheck` exits non-zero — ed99991
