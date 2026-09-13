# Instance Address Implementation Plan

> Execution state lives in `todos.md`, sibling of this file.

## Overview

The published TUI talks only to `http://localhost:8000`, hardcoded in its source, so a
person can reach a different Weles instance only by editing code and rebuilding. This
change lets a person point the TUI at an instance of their choosing through a supported
CLI action, persists that choice, and routes every request the TUI makes to it. Pointing
at a different instance replaces the previous one. It realizes slice S-02 of `auth-flow`
(AC-01, AC-02) and the frame's FR-07 / PRD FR-001: the public TUI names no particular
instance.

## Current State Analysis

The address is hardcoded in two independent places:

- `tui/src/api/client.ts:27-30` — `createClient<paths>({ baseUrl: "http://localhost:8000" })`,
  built once at module import and imported as `client` by `cards.ts`, `due.ts`,
  `notes.ts`, `sittings.ts`, and `stream.ts`.
- `tui/src/api/stream.ts:8` — `API_BASE_URL`, used by `sendMessage` for the SSE route,
  which bypasses the openapi client and calls `fetch` directly.

`tui/src/cli.tsx` calls `meow` with no flags or commands, exits when stdin/stdout is not a
TTY, then renders `<App />`. The TUI has no persisted configuration of any kind and reads
no environment variables. `tui/package.json:20` (`generate:api`) also targets localhost,
but that is a developer tool run against a local backend, not part of the published TUI.

## Desired End State

A person runs `weles instance set https://my-instance.example` once. Every later `weles`
launch sends all capture, notes, cards, due, and sitting requests to that address.
`weles instance` prints the configured address. Running `weles instance set` with another
address replaces the stored one, and the next launch reaches only the new instance.
Launching `weles` with no configured instance does not start the TUI. It prints how to
point it at one and exits non-zero. The built bundle `tui/dist/cli.js` contains no
instance address.

Verify by building the TUI, pointing it at a running local backend through
`instance set`, using it, then pointing it at a port with no backend and confirming that
the TUI shows load failures rather than the previous instance's data.

### Key Discoveries:

- `openapi-fetch` fixes `baseUrl` when `createClient` runs (`tui/src/api/client.ts:27`),
  and Node's `Request` rejects a relative URL. An empty `baseUrl` plus late prefixing is
  therefore not viable; the client has to be created for a concrete address.
- `tui/test/sittings.test.ts:143,191,266` and `tui/test/client.test.ts:16-42` assert
  literal `http://localhost:8000/...` URLs through `vi.stubGlobal("fetch")`. A test-wide
  configured address keeps them valid without editing them.
- `tui/test/app.test.tsx:46-72` replaces `api/stream`, `api/notes`, and `api/sittings`
  with `vi.mock(..., importOriginal)`, so App-level tests never resolve an address
  themselves.
- meow 14 supports `commands: string[]` (`tui/node_modules/meow/readme.md`, `commands`).
  Parsing stops at the first non-flag argument, `cli.command` names it, and the remaining
  arguments arrive in `cli.input`. With no command, `cli.command` is `undefined` and meow
  does not exit.
- `context/adrs/tui-stack/decision.md` names meow as the entry-point parser in front of
  the Ink tree, so the CLI action belongs there rather than inside an Ink screen.

## What We're NOT Doing

- Switching instances inside a running TUI. The address is resolved once per process; a
  running TUI keeps its address until it is restarted.
- Tying a sign-in to its instance. Per the roadmap, whichever of S-01 and S-02 lands
  second owns that interaction; S-01 lands second and owns it.
- Remembering several instances at once (frame out-of-scope).
- An environment variable or launch flag that overrides the stored address.
- Probing the instance (`/health` or otherwise) when the address is set.
- Changing `generate:api` in `tui/package.json`, which stays on localhost as a local
  developer tool.
- Any backend, database, or deployment change.

## Implementation Approach

A small `src/instance/` area owns the address as a value: parsing and validating it,
reading and writing it to one JSON file under the user's config directory, and the
`instance` CLI command that shows or sets it. File-system location and output are
injected as dependencies, so the command runs in tests against a temporary directory with
no patching.

The API layer stops owning an address. `src/api/instance.ts` holds the address configured
for this process and hands out an openapi client memoized per address. Every API module
calls `getClient()` instead of importing a module-level `client`, and `stream.ts` builds
its SSE URL from the same address. `src/startup.ts` decides whether the TUI may start:
a stored address yields `ready`, and a missing one yields `missing` carrying the refusal
text. `cli.tsx` becomes thin glue: it dispatches `instance` to the command before the TTY
check, and otherwise resolves startup, configures the API address, checks for a TTY, and
renders.

## Critical Implementation Details

Command dispatch must run before the TTY check in `cli.tsx`. Otherwise `weles instance
set` fails in exactly the non-interactive contexts a devcontainer setup script uses.

---

## Phase 1: Instance address stubs

### Overview

Materialize the exported symbols Phase 2's tests import: the address value and its
parser, the config store, and the `instance` command. No behaviour.

### Changes Required:

#### 1. Address value and parser

**File**: `tui/src/instance/address.ts`

**Intent**: A single typed notion of "an instance address" so no raw string reaches the
API layer unvalidated.

**Contract**: `export type InstanceAddress = string & { readonly __brand: "InstanceAddress" }`;
`export class InvalidInstanceAddressError extends Error`;
`export function parseInstanceAddress(raw: string): InstanceAddress` with an
unimplemented body that throws.

#### 2. Config store

**File**: `tui/src/instance/configStore.ts`

**Intent**: Persist the chosen address across launches in one file.

**Contract**: `export type ConfigLocation = { env: NodeJS.ProcessEnv; homeDir: string }`;
`export function configFilePath(location: ConfigLocation): string`;
`export async function readInstanceAddress(location: ConfigLocation): Promise<InstanceAddress | null>`;
`export async function writeInstanceAddress(location: ConfigLocation, address: InstanceAddress): Promise<void>`.
Unimplemented bodies.

#### 3. `instance` command

**File**: `tui/src/instance/command.ts`

**Intent**: The supported action a person uses to show or set the instance, runnable
without rendering Ink.

**Contract**: `export type InstanceCommandDeps = { location: ConfigLocation; out: (line: string) => void; err: (line: string) => void }`;
`export async function runInstanceCommand(args: string[], deps: InstanceCommandDeps): Promise<number>`,
which returns the process exit code. Unimplemented body.

### Success Criteria:

#### Automated Verification:

- `cd tui && pnpm typecheck` passes with the three new modules
- `cd tui && pnpm lint` passes

---

## Phase 2: Instance address behaviour

### Overview

Make the address parser, the config store, and the `instance` command real.

### Changes Required:

#### 1. Address parsing

**File**: `tui/src/instance/address.ts`

**Intent**: Accept only addresses the TUI can actually call, normalized so that two
spellings of one instance compare equal.

**Contract**: `parseInstanceAddress` accepts `http:` and `https:` URLs. It rejects any
other scheme, embedded credentials, a query string, a fragment, and unparseable input by
throwing `InvalidInstanceAddressError` with a message naming the reason. It returns
origin plus path with trailing `/` removed, so `https://host/` and `https://host` both
yield `https://host`, and a path prefix such as `https://host/weles` is kept.

#### 2. Config persistence

**File**: `tui/src/instance/configStore.ts`

**Intent**: One stable location per user, following XDG where set.

**Contract**: `configFilePath` is `$XDG_CONFIG_HOME/weles/config.json` when
`XDG_CONFIG_HOME` is a non-empty value, and `<homeDir>/.config/weles/config.json`
otherwise. The file is JSON `{ "instanceAddress": "<address>" }`.
`writeInstanceAddress` creates the directory if needed and replaces the stored address.
`readInstanceAddress` returns `null` when the file is absent, and the parsed address
otherwise. A stored value that fails `parseInstanceAddress` surfaces as
`InvalidInstanceAddressError`.

#### 3. Command behaviour

**File**: `tui/src/instance/command.ts`

**Intent**: `weles instance` shows, `weles instance set <address>` replaces.

**Contract**:

- `[]` prints the stored address and returns `0`. With none stored, it writes
  `No Weles instance configured. Run: weles instance set <address>` to `err` and returns `1`.
- `["set", address]` validates the address, stores it, prints
  `Weles instance set to <address>. Restart any running Weles TUI to use it.`, and
  returns `0`. An invalid address writes the parser's message to `err`, leaves the stored
  value untouched, and returns `2`.
- Any other argument shape writes a usage line to `err` and returns `2`.

### Success Criteria:

#### Automated Verification:

- `cd tui && pnpm vitest run test/instanceCommand.test.ts test/instanceAddress.test.ts` passes
- `cd tui && pnpm test` passes
- `cd tui && pnpm typecheck` and `pnpm lint` pass

---

## Phase 3: Startup and API routing stubs

### Overview

Materialize the symbols Phase 4's tests import: the process-wide address holder, the
per-address client accessor, and the startup decision. Add the test-wide configured
address.

### Changes Required:

#### 1. API instance holder

**File**: `tui/src/api/instance.ts`

**Intent**: The one place the API layer learns which instance to call.

**Contract**: `export class InstanceNotConfiguredError extends Error`;
`export function setInstanceAddress(address: InstanceAddress): void`;
`export function instanceAddress(): InstanceAddress`;
`export function getClient(): Client<paths>`, where `Client` is `openapi-fetch`'s client
type. Unimplemented bodies.

#### 2. Startup decision

**File**: `tui/src/startup.ts`

**Intent**: A testable answer to "may the TUI start, and against what?".

**Contract**: `export type StartupDecision = { kind: "ready"; address: InstanceAddress } | { kind: "missing"; message: string }`;
`export async function resolveStartup(location: ConfigLocation): Promise<StartupDecision>`.
Unimplemented body.

#### 3. Test-wide address

**File**: `tui/test/setup.ts`, `tui/vitest.config.ts`

**Intent**: Existing tests that assert `http://localhost:8000/...` keep a configured
address once the hardcode is gone.

**Contract**: `setup.ts` calls `setInstanceAddress(parseInstanceAddress("http://localhost:8000"))`;
`vitest.config.ts` adds `setupFiles: ["test/setup.ts"]`.

### Success Criteria:

#### Automated Verification:

- `cd tui && pnpm typecheck` passes
- `cd tui && pnpm lint` passes

---

## Phase 4: Startup and API routing behaviour

### Overview

Route every request to the configured instance, remove both hardcoded addresses, and
wire the CLI so `weles` refuses to start without an instance.

### Changes Required:

#### 1. Holder and memoized client

**File**: `tui/src/api/instance.ts`

**Intent**: Requests always target the address configured for this process.

**Contract**: `instanceAddress()` throws `InstanceNotConfiguredError` before any
`setInstanceAddress`. `getClient()` returns an openapi client whose `baseUrl` is
`instanceAddress()` and whose `fetch` is `delegatedFetch`. It is created lazily and
recreated when the address differs from the one it was built for, so no request made
after `setInstanceAddress(b)` reaches `a`.

#### 2. API modules off the hardcode

**File**: `tui/src/api/client.ts`, `tui/src/api/cards.ts`, `tui/src/api/due.ts`,
`tui/src/api/notes.ts`, `tui/src/api/sittings.ts`, `tui/src/api/stream.ts`

**Intent**: No module in the published TUI names an address.

**Contract**: `client.ts` keeps `delegatedFetch` and drops the module-level `client`
export. Every `client.GET/POST` call becomes `getClient().GET/POST`. `stream.ts` removes
`API_BASE_URL`, and `sendMessage` fetches `${instanceAddress()}/capture-sessions/<id>/messages`.

#### 3. Startup decision

**File**: `tui/src/startup.ts`

**Intent**: Refuse to start rather than guess an instance.

**Contract**: `resolveStartup` returns `ready` with the stored address, or `missing`
with the message `No Weles instance configured. Run: weles instance set <address>`.

#### 4. CLI wiring

**File**: `tui/src/cli.tsx`

**Intent**: One entry point for the TUI and the `instance` action.

**Contract**: `meow` is declared with `commands: ["instance"]` and help text listing
`weles`, `weles instance`, and `weles instance set <address>`. When the command is
`instance`, `cli.tsx` exits with `runInstanceCommand(cli.input, …)` before the TTY check.
Otherwise it awaits `resolveStartup`. On `missing` it prints the message and exits `1`.
On `ready` it calls `setInstanceAddress`, performs the existing TTY check, and renders
`<App />`. `location` is `{ env: process.env, homeDir: os.homedir() }`.

### Success Criteria:

#### Automated Verification:

- `cd tui && pnpm vitest run test/instanceRouting.test.ts test/startup.test.ts` passes
- `cd tui && pnpm test` passes, including the unchanged `sittings.test.ts` and `client.test.ts`
- `cd tui && pnpm typecheck` and `pnpm lint` pass

#### Manual Verification:

- `cd tui && pnpm build && XDG_CONFIG_HOME=$(mktemp -d) node dist/cli.js` prints the not-configured message and exits 1 (`echo $?`)
- `node dist/cli.js instance set ftp://example` prints a scheme error and exits 2
- `node dist/cli.js instance set http://localhost:8000/`, then `node dist/cli.js instance` prints `http://localhost:8000`
- With the backend running, `pnpm start` loads the notes list and due count from that instance
- `node dist/cli.js instance set http://localhost:8999`, then `pnpm start` shows load failures and none of the previous instance's notes
- `grep -c "localhost:8000" dist/cli.js` prints `0`

---

## Testing Strategy

### Unit Tests:

- Phase 2: address parsing (scheme rejection, trailing-slash normalization) and the
  `instance` command against a temporary `XDG_CONFIG_HOME` (set then show round-trip, a
  second set replaces the first, show with nothing stored reports it and returns
  non-zero).
- Phase 4: with `fetch` stubbed, an openapi-backed call such as `listNotes` requests the
  configured address; `sendMessage` requests the configured address. After
  `setInstanceAddress` to a second address, no request reaches the first (AC-02).
  `resolveStartup` over an empty config directory returns `missing` naming
  `weles instance set`.

### Integration Tests:

None. The TUI has no integration lane; the Manual steps run the built bundle against a
live backend.

### Manual Testing Steps:

See the Phase 4 Manual Verification list.

## Performance Considerations

One small JSON file read at startup. The memoized client means no per-request client
construction.

## Migration Notes

Existing local setups must run `weles instance set http://localhost:8000` once after this
lands, because the TUI no longer falls back to localhost.

## References

- Slice: `context/efforts/auth-flow/roadmap.md` (S-02)
- Stories: `context/efforts/auth-flow/stories.md` (US-01, AC-01, AC-02)
- PRD: `context/efforts/auth-flow/prd.md` (FR-001, NFR on instance-agnostic artifacts)
- Frame: `context/efforts/auth-flow/frame.md` (FR-07, one instance at a time)
- `context/adrs/tui-stack/decision.md` — meow at the entry point, openapi-fetch client
