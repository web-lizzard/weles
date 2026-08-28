# TUI Bootstrap Implementation Plan

## Overview

Install and bootstrap the Node.js/TypeScript TUI client decided in `context/adrs/tui-stack` and `context/adrs/repo-shape`: a pnpm-managed Ink CLI at top-level `tui/`, with its full dependency set installed and a runnable skeleton — a `meow`-parsed entry point rendering a minimal Ink root component — so later changes (real screens, live OpenAPI-generated client, Zustand-backed background state) build on a working foundation instead of starting from zero.

## Current State Analysis

The repository holds only `context/` planning artifacts, devcontainer/tooling config, and the unimplemented `backend-bootstrap` plan (Python side, not yet built) — no Node code and no pnpm workspace exist yet. The devcontainer already provisions Node 22 via the `ghcr.io/devcontainers/features/node:1` feature (`.devcontainer/devcontainer.json`), but has no `pnpm`/`corepack` activation step. `context/adrs/tui-stack/decision.md` fixes the full stack (TypeScript, pnpm, Ink, Zustand, openapi-typescript + openapi-fetch, tsup, meow, Vitest + ink-testing-library); `context/adrs/repo-shape/decision.md` fixes the boundary (TUI stays thin, talks to the backend only over HTTP, no business logic). Both ADRs are still `status: open` — this change is one `implements` step toward closing them, not the only one.

### Key Discoveries:

- `.devcontainer/devcontainer.json` uses the Node feature, not a Dockerfile `RUN` step, for Node itself — a `corepack enable` step belongs in `post-create.d/` (runtime), not the Dockerfile (build-time, before features layer in), so it reliably sees the feature-installed Node.
- `post-create.d/` runs numbered scripts in sorted order (`08-install-ordo.sh`, `10-pre-commit.sh`, `15-install-claude-code.sh`); `backend-bootstrap`'s plan (unimplemented) reserves `20-backend-sync.sh` — this change's scripts must not collide with that number.
- Ink 7.x and meow 14.x are both ESM-only with a Node `>=22` engines floor — the `tui/` package must be `"type": "module"`, and the workspace's effective Node floor is 22 (already satisfied by the existing devcontainer feature).
- tsup's shebang handling only `chmod +x`'s the emitted chunk when the source file's first line is already `#!/usr/bin/env node` — it does not inject one via `banner`; combining a source shebang with a `banner` shebang duplicates the line (tsup#684).
- `openapi-typescript`/`openapi-fetch` codegen has no live schema to run against yet (`backend-bootstrap`'s `/health`/`/openapi.json` isn't implemented) — the wiring is scaffolded with a checked-in placeholder `paths` interface so the hand-written client still typechecks, and the `generate:api` script is safe to commit unrun (not a `pnpm install` lifecycle hook).
- No prior Node code exists, so there is no legacy layout or dependency set to reconcile against — this is a from-scratch scaffold, not a migration.

## Desired End State

A developer can rebuild the devcontainer, run `pnpm install` at the repo root, run `pnpm --filter tui build`, and either run `node tui/dist/cli.js` or `pnpm --filter tui exec weles` to see the bootstrap greeting rendered by Ink. The package layout already separates the CLI entry (`cli.tsx`), the Ink root (`app.tsx`), the API-client wiring (`api/`), and the cross-cutting state store (`store/`) so the next change (a real screen, live-generated API types, or the flashcard-status store) has a boundary to slot into rather than one to invent.

Verification: `pnpm install` at repo root exits 0; `pnpm --filter tui typecheck` and `pnpm --filter tui build` exit 0; `pnpm --filter tui test` passes; `node tui/dist/cli.js` prints the bootstrap greeting.

### Key Discoveries:

- No prior Node code exists, so there is no legacy layout or dependency set to reconcile against — this is a from-scratch scaffold, not a migration.

## What We're NOT Doing

- No real OpenAPI codegen run — the `generate:api` script and a placeholder `paths` type are committed, but nothing is generated against a live schema. `backend-bootstrap` isn't implemented yet, so there's no schema to generate against.
- No real Zustand store fields — an empty placeholder store module is committed; the flashcard-generation/background-status shape is a future change's decision, per `tui-stack`.
- No real screens, navigation, or command surface beyond the single bootstrap greeting — `meow`'s `flags` object stays empty.
- No auth/session handling on the API-client wrapper — `repo-shape` defers the auth mechanism entirely; the client wrapper has no token/header logic yet.
- No linting/formatting tooling (ESLint, Prettier) — not part of `tui-stack`'s decision; out of scope here.
- No CI pipeline changes beyond what the devcontainer needs to install and sync.

## Implementation Approach

Order phases so each one's manual verification is actually checkable with what came before: `pnpm` has to be activated in the devcontainer before a pnpm-managed workspace can be scaffolded, and the project skeleton has to exist before there's anywhere to put a component or a CLI entry. The one genuinely TDD'able surface in this change — the root Ink component's render output — is split stub-then-behavior per `references/tdd-ability.md`: the stub phase commits the `App` and `cli.tsx` symbols (so a test has something concrete to import and render), the behavior phase wires the real greeting body, written to satisfy a test authored against the stub.

## Phase 1: Devcontainer — enable pnpm + workspace root

### Overview

Activate `pnpm` in the devcontainer via `corepack` (Node 22 is already present via the existing feature) and lay down the pnpm workspace root that `tui/` will join in Phase 2.

### Changes Required:

#### 1. Devcontainer pnpm activation

**File**: `.devcontainer/post-create.d/12-enable-pnpm.sh` (new)

**Intent**: Make `pnpm` available in the integrated terminal on every container (re)creation, via `corepack` rather than a separate install step, since Node 22 ships `corepack` already.

**Contract**: Executable script, runs `corepack enable` then `corepack prepare pnpm@11.24.0 --activate`. Numbered `12-` to sort before the existing `15-install-claude-code.sh` and clear of `backend-bootstrap`'s reserved `20-backend-sync.sh`.

#### 2. pnpm workspace root

**File**: `pnpm-workspace.yaml` (new)

**Intent**: Declare the workspace membership so `tui/` is discoverable by `pnpm install`/`pnpm --filter` once it exists.

**Contract**: `packages: ["tui"]` — matches `repo-shape`'s "top-level package" shape (no `packages/*` glob, since only one Node package exists).

#### 3. Root package manifest

**File**: `package.json` (new, repo root)

**Intent**: Give the workspace a root manifest pinning the package manager and the Node floor, without itself being a publishable package.

**Contract**: `{"name": "weles", "private": true, "engines": {"node": ">=22"}, "packageManager": "pnpm@11.24.0"}`.

#### 4. Ignore Node build artifacts

**File**: `.gitignore`

**Intent**: Keep `node_modules/` and build output out of version control, matching the existing `.pnpm-store/` entry already present.

**Contract**: Adds `node_modules/` and `dist/` entries.

### Success Criteria:

#### Automated Verification:
- None — infra/config change, no automated assertion path in this stack.

#### Manual Verification:
- Rebuild the devcontainer ("Dev Containers: Rebuild Container").
- `pnpm --version` succeeds inside the rebuilt container.
- `ordo status` still succeeds (confirms this phase didn't disturb the existing post-create flow).

---

## Phase 2: TUI project scaffolding

### Overview

Create the `tui/` package: a pnpm-managed project with the full dependency set from `tui-stack`, laid out with the CLI-entry/root-component/API-client/store separation, wired into the devcontainer's post-create flow.

### Changes Required:

#### 1. TUI package manifest

**File**: `tui/package.json` (new)

**Intent**: Establish `tui/` as a private, ESM, `pnpm`-managed package with the runtime and dev dependency set `tui-stack` names, plus the scripts later phases and future changes call.

**Contract**: `"name": "tui"`, `"private": true`, `"type": "module"`, `"bin": {"weles": "./dist/cli.js"}`, `"engines": {"node": ">=22"}`. Scripts: `build` (`tsup`), `dev` (`tsup --watch`), `test` (`vitest run`), `typecheck` (`tsc --noEmit`), `generate:api` (`openapi-typescript http://localhost:8000/openapi.json -o src/api/generated/schema.d.ts` — the backend's default FastAPI schema route, not yet live). Runtime deps: `ink`, `react`, `meow`, `openapi-fetch`, `zustand`. Dev deps: `@types/react`, `ink-testing-library`, `openapi-typescript`, `tsup`, `typescript`, `vitest` — all caret ranges, `pnpm-lock.yaml` does the pinning.

#### 2. TypeScript config

**File**: `tui/tsconfig.json` (new)

**Intent**: Configure the compiler for an ESM, JSX, bundler-resolved package matching `ink`/`openapi-fetch`'s own module expectations.

**Contract**: `"module": "ESNext"`, `"moduleResolution": "Bundler"`, `"jsx": "react-jsx"`, `"target": "ES2022"`, `"strict": true`, `"outDir": "dist"`, `"include": ["src", "test"]`.

#### 3. tsup bundler config

**File**: `tui/tsup.config.ts` (new)

**Intent**: Bundle the CLI entry to a single executable ESM file for fast cold start, per `tui-stack`'s tsup decision.

**Contract**: `entry: ["src/cli.tsx"]`, `format: ["esm"]`, `platform: "node"`, `target: "node22"`, `clean: true`, `dts: false`. No `banner` — the shebang lives in `src/cli.tsx` itself (Phase 3), and tsup's own shebang plugin only `chmod`s the already-shebang'd output.

#### 4. Vitest config

**File**: `tui/vitest.config.ts` (new)

**Intent**: Configure the test runner `tui-stack` names, ready for Phase 4's `ink-testing-library` test.

**Contract**: `test.environment: "node"`.

#### 5. Directory skeleton

**File**: `tui/src/{cli.tsx,app.tsx}`, `tui/src/api/{client.ts,generated/schema.d.ts}`, `tui/src/store/index.ts`, `tui/test/` (all new, `cli.tsx`/`app.tsx` populated in Phase 3)

**Intent**: Commit the CLI-entry / root-component / API-client / cross-cutting-store boundary to the file tree before real behavior exists, so the next real feature has an obvious home.

**Contract**: `src/api/generated/schema.d.ts` — placeholder `export interface paths {}`, marked with a one-line comment that it's disposable and overwritten by `generate:api`. `src/api/client.ts` — `export const client = createClient<paths>({ baseUrl: "http://localhost:8000" })` via `openapi-fetch`, importing the placeholder `paths` type. `src/store/index.ts` — an empty Zustand store: `export const useAppStore = create(() => ({}))`, no fields yet, per `tui-stack`'s "background-task/notification state only" scope. `tui/test/` created empty, holds Phase 4's test file.

#### 6. Devcontainer sync step

**File**: `.devcontainer/post-create.d/22-tui-sync.sh` (new)

**Intent**: Make the workspace's dependencies installed automatically on container (re)creation, same pattern as the existing `ordo`/pre-commit/Claude Code steps.

**Contract**: `pnpm install` (run from repo root, installs all workspace packages), executable. Numbered `22-` — after `backend-bootstrap`'s reserved `20-backend-sync.sh`, no ordering dependency between the two.

### Success Criteria:

#### Automated Verification:
- `pnpm install` (repo root) exits 0.
- `pnpm --filter tui typecheck` exits 0.
- `pnpm --filter tui build` exits 0.

#### Manual Verification:
- None beyond the automated checks above — this phase is pure scaffolding.

---

## Phase 3: Bootstrap contract — stubs

### Overview

Commit the symbol Phase 4's test imports and renders: the `App` root component, wired into `cli.tsx`'s `meow` + `render` entry — placeholder body, no real greeting yet.

### Changes Required:

#### 1. Root component stub

**File**: `tui/src/app.tsx`

**Intent**: Fix the `App` component's export shape ahead of a real render body, so Phase 4's test can import a stable symbol.

**Contract**: `export default function App()` returning `null` — a valid React function component, no props, no real output yet.

#### 2. CLI entry wiring

**File**: `tui/src/cli.tsx`

**Intent**: Wire the process entry point — shebang, `meow` argv parsing, `render(<App/>)` — ahead of `App` having real output.

**Contract**: First line `#!/usr/bin/env node`. Calls `meow()` with `importMeta: import.meta` and an empty `flags: {}` (get `--help`/`--version` for free, no real flags yet), then `render(<App />)`.

### Success Criteria:

#### Automated Verification:
- `pnpm --filter tui typecheck` exits 0.
- `pnpm --filter tui build` exits 0.

#### Manual Verification:
- None — stub phase, no observable behavior yet.

---

## Phase 4: Bootstrap contract — behavior

### Overview

Wire real behavior behind Phase 3's stub: `App` renders the bootstrap greeting — and write the test that proves the contract.

### Changes Required:

#### 1. Root component — real render

**File**: `tui/src/app.tsx`

**Intent**: Give the bootstrap skeleton one observable, testable output — proof the Ink render pipeline works end to end before the first real screen replaces it.

**Contract**: `App` renders `<Text>Weles TUI — bootstrap OK</Text>`.

### Success Criteria:

#### Automated Verification:
- `pnpm --filter tui test` passes, covering: `App` renders `"Weles TUI — bootstrap OK"`, asserted via `ink-testing-library`'s `render(<App/>).lastFrame()`.

#### Manual Verification:
- `pnpm --filter tui build`, then `node tui/dist/cli.js` (or `pnpm --filter tui exec weles`) prints `Weles TUI — bootstrap OK` to the terminal.

### Review r1

Artifact: `reviews/2026-08-28-r1-impl-review.md`

- `R1-F1` — `pnpm --filter tui typecheck` exits non-zero
  Fix: Test imports must resolve under `tsc --noEmit` without enabling `allowImportingTsExtensions`; `pnpm --filter tui typecheck` must exit 0 as required by Phase 2 and Phase 3 automated verification.

---

## Testing Strategy

### Unit Tests:
- `App` root-component render contract (Phase 4): renders the expected bootstrap greeting.

### Integration Tests:
- None — no HTTP/store integration exists yet to assert against.

### Manual Testing Steps:
- Rebuild devcontainer, confirm `pnpm --version` works and `ordo status` still succeeds (Phase 1).
- `pnpm install` + typecheck/build smoke-check (Phase 2).
- `node tui/dist/cli.js` prints the bootstrap greeting (Phase 4).

## Performance Considerations

None — no load-bearing code path exists yet; this change only bootstraps the project.

## Migration Notes

None — this is a from-scratch scaffold, not a migration of existing code or data.

## References

- `context/adrs/tui-stack/decision.md` — TypeScript/pnpm/Ink/Zustand/openapi-client/tsup stack decision.
- `context/adrs/repo-shape/decision.md` — monorepo shape, TUI/backend boundary, auth deferral.
- `context/changes/tui-bootstrap/change.md` — this change's identity and scope note.
- `context/changes/backend-bootstrap/plan.md` — sibling bootstrap change; devcontainer post-create numbering and phase-shape precedent.
- [Ink](https://github.com/vadimdemedes/ink) — `engines.node >=22`, ESM-only.
- [meow](https://github.com/sindresorhus/meow) — `importMeta`/ESM-only usage.
- [tsup shebang handling](https://github.com/egoist/tsup) — chmod-only plugin, no shebang injection.
- [openapi-typescript](https://openapi-ts.dev/cli) / [openapi-fetch](https://openapi-ts.dev/openapi-fetch/) — codegen CLI and typed fetch wrapper.
- [ink-testing-library](https://github.com/vadimdemedes/ink-testing-library) — `render().lastFrame()` test pattern.
- [pnpm](https://pnpm.io/installation) — current stable `11.24.0` via `corepack`.
