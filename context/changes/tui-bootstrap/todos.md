---
change_id: tui-bootstrap
current_phase: 1
next_step: 1.1
next_command: /implement tui-bootstrap phase 1
updated: 2026-08-28
---

### Phase 1: Devcontainer — enable pnpm + workspace root

#### Manual

- [ ] 1.1 Rebuild the devcontainer
- [ ] 1.2 `pnpm --version` succeeds inside the rebuilt container
- [ ] 1.3 `ordo status` still succeeds

### Phase 2: TUI project scaffolding

#### Automated

- [ ] 2.1 `pnpm install` (repo root) exits 0
- [ ] 2.2 `pnpm --filter tui typecheck` exits 0
- [ ] 2.3 `pnpm --filter tui build` exits 0

### Phase 3: Bootstrap contract — stubs

#### Automated

- [ ] 3.1 `pnpm --filter tui typecheck` exits 0
- [ ] 3.2 `pnpm --filter tui build` exits 0

### Phase 4: Bootstrap contract — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 `pnpm --filter tui test` passes (App renders `"Weles TUI — bootstrap OK"`)

#### Manual

- [ ] 4.2 `pnpm --filter tui build` then `node tui/dist/cli.js` prints `Weles TUI — bootstrap OK`
