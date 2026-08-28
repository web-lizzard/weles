# TUI Bootstrap — Plan Brief

> Full plan: `plan.md`

## What & Why

Install and bootstrap the Node.js/TypeScript TUI client decided in `context/adrs/tui-stack` and `context/adrs/repo-shape`: a `pnpm`-managed Ink CLI at top-level `tui/`, with its full dependency set installed and a runnable, `meow`-parsed skeleton that renders one greeting — so the next capability (a real screen, live OpenAPI codegen, the Zustand background-status store) has a working foundation to build into.

## Starting Point

No Node code or pnpm workspace exists yet — only `context/` planning artifacts, and a devcontainer that already provisions Node 22 (via feature) but has no `pnpm`/`corepack` activation. The sibling `backend-bootstrap` change (same shape, Python side) is planned but not yet implemented, so no live backend or OpenAPI schema exists to generate a client against.

## Desired End State

`pnpm install` at the repo root → `pnpm --filter tui build` bundles the CLI → `node tui/dist/cli.js` (or `pnpm --filter tui exec weles`) prints `Weles TUI — bootstrap OK`, proving the Ink render pipeline works end to end.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| OpenAPI client, no live schema yet | Scaffold wiring + placeholder `paths` type, defer real codegen | `backend-bootstrap` isn't implemented, so there's no schema to generate against; the wrapper still typechecks against a placeholder. | User |
| CLI entry behavior | Minimal Ink "hello" screen | Proves the render pipeline works end to end, mirroring `backend-bootstrap`'s `/health` as a runnable-skeleton proof. | User |
| TDD scope | Root `App` component render is the one testable contract | Parallels `backend-bootstrap`'s health-endpoint test as the single real behavioral contract in an otherwise-scaffolding change. | User |
| Zustand store | Empty placeholder module now, no fields | Gives the next change (flashcard-status polling) an obvious home to extend, per `tui-stack`'s scoped-exception intent. | User |
| Backend location | top-level `tui/` | Matches `repo-shape`'s "two top-level packages" monorepo shape. | Plan |
| Package manager activation | `corepack enable` + `corepack prepare pnpm@11.24.0` in `post-create.d/` | Node 22 (already provisioned via devcontainer feature) ships `corepack`; no separate pnpm install step needed. | Plan |
| Devcontainer script numbering | `12-enable-pnpm.sh`, `22-tui-sync.sh` | Sorts clear of `backend-bootstrap`'s reserved `20-backend-sync.sh`; no ordering dependency between the two stacks. | Plan |

## Scope

**In scope:** devcontainer pnpm activation; pnpm workspace root; `tui/` project scaffold (package manifest, tsconfig, tsup, vitest, dependencies); CLI-entry/root-component/API-client/store directory boundary; a runnable Ink skeleton with one tested greeting.

**Out of scope:** real OpenAPI codegen run (no live schema yet); real Zustand store fields; any screen beyond the bootstrap greeting; auth/session logic on the API client; linting/formatting tooling; CI pipeline changes beyond devcontainer install/sync.

## Architecture / Approach

`tui/src/`: `cli.tsx` (shebang + `meow` argv parsing + `render()`, the only file that knows about argv), `app.tsx` (root Ink component, testable in isolation), `api/` (`client.ts` wrapping a placeholder-typed `openapi-fetch` client, `generated/schema.d.ts` disposable until real codegen runs), `store/` (empty Zustand placeholder). Devcontainer moves from Node-feature-only to Node-feature-plus-`corepack`-activated-`pnpm`, alongside a new pnpm workspace root at repo top level.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Devcontainer — enable pnpm + workspace root | `pnpm` activated via `corepack`, workspace root files | Script-number collision with `backend-bootstrap`'s reserved `20-backend-sync.sh` — avoided by using `12-`/`22-` |
| 2. TUI project scaffolding | `pnpm`-managed `tui/` project, directory boundary, dependencies installed | tsup `banner` + source-shebang duplication if config strays from source-only shebang handling |
| 3. Bootstrap contract — stubs | `App`/`cli.tsx` symbols committed, no real behavior | None significant — pure interface commitment |
| 4. Bootstrap contract — behavior | Real greeting render, test passing | None significant — small, well-scoped contract |

**Prerequisites:** none — first Node code in the repository.
**Estimated effort:** small (4 phases, no real screens or state yet).

## Open Risks & Assumptions

- Assumes `backend-bootstrap` remains unimplemented through this change — the `generate:api` script points at `http://localhost:8000/openapi.json`, which stays a no-op until that change ships.
- Assumes pnpm `11.24.0` stays current enough through implementation; `pnpm 12` (Rust rewrite) shipped days before this plan and is deliberately not pinned yet.

## Success Criteria (Summary)

- `pnpm install` (repo root) and `pnpm --filter tui build`/`typecheck` exit 0.
- `pnpm --filter tui test` passes.
- `node tui/dist/cli.js` prints `Weles TUI — bootstrap OK`.
