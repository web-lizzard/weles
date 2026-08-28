## Context

`context/adrs/repo-shape/` already settled that the TUI is a Node.js client built on Ink, kept as a thin presentation layer with no business logic, talking to the backend exclusively over an authenticated HTTP API. `context/adrs/backend-stack/` settled the backend as FastAPI (which auto-generates an OpenAPI schema), `pydantic-ai`, SQLAlchemy, and `notion-client`. Neither of those is re-opened here — Ink and the HTTP-only client boundary are carried over unchanged. This decision covers everything the TUI-side codebase needs beyond the choice of Ink itself: language, package manager, state management, how the TUI talks to the FastAPI backend (including its streaming/async paths), the test setup, the CLI entry point, and how the client is built and distributed.

Two shapes of backend interaction matter for this decision specifically:

- **Standard request/response** — the bulk of the API surface (capture, search, remember-queue reads, etc.), which FastAPI exposes with a normal OpenAPI-described JSON contract.
- **Asynchronous/streamed work** — flashcard generation from the distill step runs asynchronously on the backend; the TUI needs to poll for completion and surface a status/notification to the user across screens that are not strictly parent-child (e.g. a background-generation indicator visible regardless of which screen is active). The backend is also expected to expose at least one SSE-style streaming endpoint for LLM-generation UX. FastAPI's `StreamingResponse` does not auto-derive an OpenAPI schema for its payload — the chunk shape has to be declared explicitly (e.g. via `responses=` on the route) for that shape to reach any type generation step at all.

This second shape is what pushed state management and the API-client strategy away from the simplest options: a single top-level React context does not model "a status that several unrelated screens need to read and that updates from a background poll" cleanly, and a plain generated request/response client does not model a stream or a poll loop at all.

## Decision

- **TypeScript** is the language for the entire TUI package, matching the Reactive/typed mental model the author brings from web development and giving a consistent typed story against the backend's Pydantic-generated contracts.
- **pnpm** (workspaces) is the package manager, used for the monorepo tooling shared between the TUI and any future Node package.
- **Ink** remains the TUI framework, carried over unchanged from `repo-shape`.
- **Zustand** is the state-management library for cross-cutting TUI state — specifically background-task status (flashcard-generation polling) and any notification-like state visible from multiple screens. It is not a place for domain/business logic, which continues to live entirely in the backend.
- **API client**, split by interaction shape:
  - Standard endpoints: a client generated from the backend's OpenAPI schema via `openapi-typescript` (types) + `openapi-fetch` (typed fetch wrapper), regenerated whenever the backend contract changes.
  - Streaming/async endpoints (SSE generation, polling for flashcard-generation completion): a small hand-written layer on top of `fetch`/`ReadableStream` (or a light SSE-parsing helper), with each chunk/poll-result typed against the response model the backend explicitly declares for that route — sourced from the same generated types as everything else, not hand-duplicated.
- **Vitest** + `ink-testing-library` for tests.
- **meow** for CLI argument/flag parsing at the process entry point, before rendering into the Ink component tree.
- **tsup** (esbuild-based) bundles the TUI to a single-file CLI with a shebang bin, for fast cold start on every invocation.

## Consequences

- Type safety on the standard request/response surface is automatic and regenerated from the backend's own schema, so the "TUI stays thin, backend owns the contract" principle from `repo-shape` is enforced by tooling rather than discipline for most of the API.
- Streaming and polling paths sit outside that automatic guarantee: their type safety depends on the backend explicitly declaring a response model on every such route. This is a discipline that has to be maintained on the backend side, not something FastAPI or the codegen step enforces on its own — an undeclared streaming route silently falls back to untyped data on the TUI side.
- Zustand is a deliberate, scoped exception to "the TUI carries no logic": it is meant to hold background-task/notification-shaped state only (e.g. flashcard-generation status), not to become a general application-state layer. Scope creep here would contradict `repo-shape`'s intent and should be treated as a signal that logic is leaking into the client.
- The exact polling strategy for flashcard-generation completion (interval, backoff, cancellation) is not decided here and is deferred to implementation or a future decision.
- pnpm workspaces give the monorepo a natural place to add more Node packages later without repository restructuring, consistent with `repo-shape`'s monorepo decision.
- tsup adds a build step to the dev loop in exchange for fast, keystroke-friendly startup — important because the daemon already absorbs Python's cold-start cost once at its own startup, and the TUI should not reintroduce an equivalent tax on its own process.

## Alternatives Considered

1. **npm or Yarn** instead of pnpm. Both are viable monorepo package managers. Rejected: pnpm is faster and more disk-efficient for workspace-heavy monorepos, with no offsetting advantage from npm's ubiquity or Yarn's PnP mode strong enough to matter for a solo project.
2. **Hand-written `fetch` wrapper** instead of a generated OpenAPI client for the standard request/response surface. Simpler, no codegen step. Rejected: hand-written types duplicate the backend's Pydantic contract by hand, and a TUI meant to stay thin is exactly the place where a silent contract drift would go unnoticed longest.
3. **Plain React state/context** instead of Zustand. This was the initial recommendation, following directly from `repo-shape`'s "TUI stays thin" principle, and it was pushed back on before being dropped. Rejected once the MVP's asynchronous flashcard-generation flow surfaced: a background-status/notification concern read from multiple, not-strictly-related screens is exactly the shape a single top-level context handles poorly (either an oversized context or heavy prop-drilling), which a small dedicated store avoids while staying scoped to non-domain state.
4. **Jest** instead of Vitest. More established, broader plugin ecosystem. Rejected: Vitest's ESM-native design and faster startup fit the rest of the TypeScript/ESM toolchain better, with no capability Jest offers here that Vitest lacks.
5. **commander or yargs** instead of `meow` for CLI argument parsing. Both are more feature-rich general-purpose CLI frameworks. Rejected: `meow` is the de facto standard in the Ink ecosystem and covers everything a flag-driven entry point into an Ink tree needs, without pulling in machinery this project doesn't use.
6. **Plain `tsc` compilation, run via `node`** instead of `tsup` bundling. Fewest moving parts, no bundler to configure. Rejected: resolving the full `node_modules`/ESM module tree on every invocation costs cold-start time that matters for a TUI meant to feel responsive to individual commands, and bundling to one file also simplifies distribution.
