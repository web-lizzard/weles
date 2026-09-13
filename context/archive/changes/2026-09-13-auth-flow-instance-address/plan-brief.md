# Instance Address — Plan Brief

> Full plan: `plan.md`

## What & Why

The published TUI only talks to a hardcoded `http://localhost:8000`, so using any other
Weles instance means editing code and rebuilding. This change adds a supported CLI action
that points the TUI at a chosen instance and persists it, so the public TUI names no
particular instance (AC-01, AC-02, FR-07).

## Starting Point

The address is hardcoded in `tui/src/api/client.ts` (openapi client) and
`tui/src/api/stream.ts` (SSE). The TUI has no persisted configuration and a flagless meow
entry point.

## Desired End State

`weles instance set <address>` stores the instance; `weles instance` shows it; every
later `weles` launch sends all requests there. Setting another address replaces it. With
no instance configured, `weles` refuses to start and says how to configure one. The
built bundle contains no address.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Shape of the action | `weles instance` / `weles instance set <address>` subcommand | meow already sits at the entry point, and a subcommand is scriptable in a devcontainer and testable without Ink. | Plan |
| No configured instance | Refuse to start with instructions, exit 1 | No request ever goes to an address the person did not choose. | Plan |
| One instance at a time | Setting a new address replaces the old one | Settled in the effort frame. | Frame |
| When a new address applies | Resolved once at process start; running TUI needs a restart | Switching in flight would require stopping polls and sessions mid-run, the complexity the in-TUI option carried. | Plan |
| Storage | `$XDG_CONFIG_HOME/weles/config.json`, else `~/.config/weles/config.json` | A single, conventional per-user location. | Plan |
| Validation | http(s) only, no credentials/query/fragment, trailing `/` trimmed, path kept | Only callable addresses are stored, and two spellings of one instance compare equal. | Plan |
| Client wiring | `getClient()` memoized per address replaces the module-level `client` | openapi-fetch fixes `baseUrl` at creation and Node rejects relative Request URLs. | Plan |
| Existing URL-asserting tests | Vitest `setupFiles` configures `http://localhost:8000` | Keeps `sittings.test.ts` and `client.test.ts` valid unchanged. | Plan |

## Scope

**In scope:** address parsing and persistence, the `instance` CLI command, routing all
API and SSE requests to the configured address, refusal to start without one.
**Out of scope:** in-flight switching, a sign-in bound to its instance (S-01 owns it),
several instances at once, env/flag overrides, probing the instance, `generate:api`, and
any backend change.

## Architecture / Approach

`src/instance/` owns the address value, its JSON store, and the `instance` command, with
file location and output injected. `src/api/instance.ts` holds the process's address and
hands out the openapi client; every API module calls `getClient()`, and `stream.ts` reads
`instanceAddress()`. `src/startup.ts` returns `ready | missing`. `cli.tsx` dispatches
`instance` before the TTY check, and otherwise configures the address and renders.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Instance address stubs | Address, store, and command symbols | None: types only |
| 2. Instance address behaviour | Validation, XDG store, `instance` show/set | File-system tests leaking into the real home directory |
| 3. Startup and API routing stubs | Holder, `getClient`, `resolveStartup`, test setup file | Setup file masking a missing address in new tests |
| 4. Startup and API routing behaviour | All requests on the configured address; CLI refusal | A missed `client.` call site still compiling against a stale import |

**Prerequisites:** none. The slice is independent of identity and the database.
**Estimated effort:** small; four short TUI phases.

## Open Risks & Assumptions

- A running TUI keeps its address until restart; `instance set` says so. AC-02 is read
  as holding from the next launch.
- Existing local setups must run `weles instance set http://localhost:8000` once.
- S-01 must key any stored sign-in by `InstanceAddress` so switching never sends one
  instance's sign-in to another.

## Success Criteria (Summary)

- `weles instance set <address>` plus a relaunch reaches only that instance.
- `weles` without a configured instance refuses with instructions and exits non-zero.
- `grep localhost:8000 tui/dist/cli.js` finds nothing.
