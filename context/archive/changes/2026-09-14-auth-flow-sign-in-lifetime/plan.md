# Sign-In Lifetime Implementation Plan

## Overview

Make the TUI usable again behind the S-01 gate. The TUI keeps a sign-in across restarts, sends it with every request, refuses to launch without a valid one, and never sends one instance's sign-in to another. When a sign-in expires during a capture conversation or a review sitting, the person is told, the in-progress work stays on screen, and they can retry after signing in again. Realizes AC-06, AC-07, AC-08 (`context/efforts/auth-flow/stories.md`, US-03) and closes the TUI half of the instance-binding handover from S-02 (`context/efforts/auth-flow/roadmap.md`, S-03).

Execution state lives in `todos.md`.

## Current State Analysis

- The backend is complete for this slice:
  - `POST /auth/sign-in` returns `access_token` and `expires_at`.
  - Every capture, notes, and remember route refuses a missing, forged, or expired token with 401 `{"code": "sign_in_required", "detail": …}` (`backend/src/adapters/auth/router.py:31-45`, `backend/src/adapters/http/errors.py:60`).
  - The lifetime is per instance, 24h by default (`backend/src/config/settings.py:46`).
- `tui/src/api/auth.ts:61-76`: `signIn` deliberately drops `access_token`. `tui/src/auth/command.ts:112-120` prints the expiry and writes nothing.
- `tui/src/api/instance.ts:31-41`: `getClient()` memoizes one `openapi-fetch` client per address, with no `Authorization` header.
- `tui/src/api/stream.ts:104-111`: `sendMessage` bypasses the client with a raw `fetch` and needs the header on its own.
- `tui/src/startup.ts:12-20`: `resolveStartup` checks only that an address is configured. `tui/src/cli.tsx:52-70` launches Ink on that alone.
- `tui/src/instance/configStore.ts:68-79`: `config.json` holds only `instanceAddress`, written with default permissions.
- `tui/src/store/chat.ts:143-155`: any send error sets `streamError` and clears `draft`.
- `tui/src/store/sitting.ts:127-133`: `sittingHttpErrorState` shows the backend `detail` verbatim, and `retry()` (`:410-431`) replays `lastAction`.

Result: today, every TUI data request is refused.

## Desired End State

- `weles sign-in <email>` stores the sign-in in `credentials.json` next to `config.json`, with mode 0600, pinned to the instance address that issued it.
- Launching `weles` with a valid stored sign-in for the configured address starts the TUI without asking to sign in again (AC-06).
- With no sign-in, a sign-in for another address, or a sign-in past its `expiresAt`, the TUI refuses to launch and names `weles sign-in <email>` (AC-07).
- Every request the TUI makes carries `Authorization: Bearer <token>` for the configured address only.
- `weles instance set` to a different address discards the stored sign-in.
- A `sign_in_required` refusal mid-capture keeps the transcript and draft and shows an expiry message. The same refusal mid-sitting shows that message in the error state, and `retry` completes the action once the person has signed in from another terminal (AC-08).

Verify with `cd tui && pnpm test && pnpm typecheck && pnpm lint`, plus the manual recipes below against a running backend.

### Key Discoveries:

- `tui/node_modules/openapi-fetch/dist/index.d.ts:236`: `client.use(middleware)` with `onRequest({ request })` is the single place to attach the header for every client call. `delegatedFetch` (`tui/src/api/client.ts:10-14`) already copies `Request` headers through.
- The token is read from disk on every request, not cached. A sign-in made in a second terminal takes effect on the running TUI's next request, and that is what makes retry after expiry work without restarting.
- `tui/test/setup.ts`: a global `beforeEach` sets the instance address. Tests that need a sign-in provider set it explicitly.
- `tui/test/startup.test.ts` and `tui/test/authCommand.test.ts`: the temp `XDG_CONFIG_HOME` pattern for anything touching config files.
- `tui/test/chat.test.ts`: `vi.mock("../src/api/stream", …)` with `importOriginal` keeps the real `SendMessageHttpError`, which is the pattern for the expiry store tests.
- TUI determinism rule (`context/foundation/testing-conventions.md`): the launch decision takes `now: Date` as input, so expiry is tested with fixed literals and no fake timers.

## What We're NOT Doing

- Any backend change. The sign-in lifetime stays at the 24h default. This is a deliberate choice made in this plan, even though the PRD asks for "a few days" (PRD Open Question 1); operators can still raise `AUTH_SIGN_IN_LIFETIME_HOURS`.
- Signing in from inside the running TUI (an Ink prompt). After expiry the person runs `weles sign-in` in another terminal. **No roadmap slice currently owns an in-TUI sign-in.** It is a follow-up to add through `/roadmap auth-flow` if wanted.
- OS keychain storage. It needs a native dependency and does not work in the Linux devcontainer.
- Remembering sign-ins for several instances. One sign-in, pinned to one address.
- Signing out (S-06), attempt limits (S-07), refresh tokens, and early invalidation.
- Expiry-specific messages for the notes list and the due-count poller. Those surfaces carry no in-progress work, so they keep their generic failed or stale state.
- BDD scenarios. There is no node-side BDD lane, so AC-06..08 are covered by the TUI unit tests below.

## Implementation Approach

There are three TDD'able units, each as a stubs phase followed by a behavior phase:

1. **Keep and send.** A credential store in `src/auth/` and a sign-in provider on the API client.
2. **Persist and guard.** The sign-in command writes the credential, an instance switch clears it, and a launch decision replaces the address-only startup check in `cli.tsx`.
3. **Expiry mid-work.** One shared expiry code and message, applied in the chat and sitting stores.

The launch guard checks the stored `expiresAt` locally, so an expired sign-in is caught before any request. Mid-session expiry is detected only from the backend's 401 code. The TUI never schedules a timer against `expiresAt`.

## Critical Implementation Details

`writeFile(path, data, { mode: 0o600 })` applies the mode only when it creates the file, so `writeSignIn` must also `chmod` an existing file to 0600.

The chat store currently clears `draft` on every error. The `sign_in_required` branch must keep it, or an approved-ready note vanishes from the screen exactly when AC-08 forbids losing work.

## Phase 1: Credential store and authorized requests — stubs

### Overview

Materialize the symbols Phase 2's tests import, with unimplemented bodies.

### Changes Required:

#### 1. Credential store interface

**File**: `tui/src/auth/credentialStore.ts`

**Intent**: Give the stored sign-in a typed home, separate from the non-secret address config.

**Contract**:
- `type StoredSignIn = { instanceAddress: InstanceAddress; token: string; expiresAt: string }`
- `credentialsFilePath(location: ConfigLocation): string`
- `readSignIn(location: ConfigLocation, address: InstanceAddress): Promise<StoredSignIn | null>`
- `writeSignIn(location: ConfigLocation, signIn: StoredSignIn): Promise<void>`
- `clearSignIn(location: ConfigLocation): Promise<void>`
- Bodies throw `"not implemented"`.

#### 2. Sign-in provider on the API client

**File**: `tui/src/api/instance.ts`, `tui/src/api/stream.ts`

**Intent**: One seam through which every request learns the current token.

**Contract**:
- `type SignInProvider = () => Promise<string | null>`
- `setSignInProvider(provider: SignInProvider): void`
- `authorizationHeaders(): Promise<Record<string, string>>`
- Bodies are unimplemented. `stream.ts` is not changed yet beyond importing nothing new.

### Success Criteria:

#### Automated Verification:
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 2: Credential store and authorized requests — behavior

### Overview

Store a sign-in safely and send it with every request to its own instance.

### Changes Required:

#### 1. Credential store

**File**: `tui/src/auth/credentialStore.ts`

**Intent**: The sign-in survives restarts, is readable only by its owner, and is never offered to a different address.

**Contract**:
- The path is `<XDG_CONFIG_HOME or ~/.config>/weles/credentials.json`, resolved like `configFilePath`.
- `writeSignIn` writes JSON and leaves the file at mode 0600, whether it created the file or replaced one.
- `readSignIn` returns `null` when the file is absent, unparseable, missing a field, or pinned to an address other than `address`.
- `clearSignIn` removes the file, and is a no-op when it is absent.

#### 2. Authorization on every request

**File**: `tui/src/api/instance.ts`, `tui/src/api/stream.ts`

**Intent**: Both request paths carry the token, and nothing else does.

**Contract**:
- `getClient()` registers an `onRequest` middleware on each newly created client. It sets `Authorization: Bearer <token>` when the provider yields a token, and sets no header when the provider is unset or yields `null`.
- `authorizationHeaders()` returns `{ Authorization: "Bearer <token>" }` or `{}`.
- `sendMessage` spreads `await authorizationHeaders()` into its `fetch` headers.
- The provider is called per request, with no caching.

#### 3. Tests

**File**: `tui/test/credentialStore.test.ts`, `tui/test/authorizedRequests.test.ts`

**Intent**: Pin the storage and header contracts.

**Contract**:
- A written sign-in reads back for its address, and the file mode is 0600, including after overwriting a pre-existing 0644 file.
- `readSignIn` for a different address returns `null`.
- `listNotes` and `sendMessage` both send `Authorization: Bearer <token>` taken from the provider, and send no header when the provider yields `null`.

### Success Criteria:

#### Automated Verification:
- Credential store and request tests pass: `cd tui && pnpm vitest run test/credentialStore.test.ts test/authorizedRequests.test.ts`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 3: Sign-in persistence, instance binding, launch guard — stubs

### Overview

Widen the sign-in outcome and materialize the launch decision, with unimplemented bodies.

### Changes Required:

#### 1. Sign-in outcome carries the token

**File**: `tui/src/api/auth.ts`, `tui/src/auth/command.ts`, `tui/src/instance/command.ts`

**Intent**: The token can reach the command that stores it.

**Contract**:
- `SignInOutcome`'s success member becomes `{ kind: "signed_in"; token: string; expiresAt: string }`.
- `AuthCommandDeps` and `InstanceCommandDeps` are unchanged. Both commands already receive `location`.
- The module docstrings that say "S-03 keeps it" are updated to describe the stored credential.

#### 2. Launch decision

**File**: `tui/src/startup.ts`, `tui/src/cli.tsx`

**Intent**: A single decision for whether the interactive TUI may start.

**Contract**:
- ```ts
  type LaunchDecision =
    | { kind: "ready"; address: InstanceAddress }
    | { kind: "missing"; message: string }
    | { kind: "signed_out"; message: string }
    | { kind: "expired"; message: string };
  ```
- `resolveLaunch(location: ConfigLocation, now: Date): Promise<LaunchDecision>`. The body is unimplemented.
- `resolveStartup` stays as it is, for the `register` and `sign-in` commands.

### Success Criteria:

#### Automated Verification:
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing TUI suite still passes: `cd tui && pnpm test`

---

## Phase 4: Sign-in persistence, instance binding, launch guard — behavior

### Overview

Store the sign-in on success, drop it when the instance changes, and refuse to launch without a valid one.

### Changes Required:

#### 1. Sign-in API and command

**File**: `tui/src/api/auth.ts`, `tui/src/auth/command.ts`

**Intent**: A successful `weles sign-in` is remembered for the instance that accepted it (AC-06).

**Contract**:
- `signIn` maps 200 to `{ kind: "signed_in", token: data.access_token, expiresAt: data.expires_at }`.
- `runSignInCommand` on `signed_in` calls `writeSignIn(location, { instanceAddress: decision.address, token, expiresAt })` before printing the confirmation and returning 0.
- `invalid_credentials` writes nothing and leaves any existing credential untouched.

#### 2. Instance switch clears the sign-in

**File**: `tui/src/instance/command.ts`

**Intent**: After a switch, no sign-in from the previous instance survives on disk.

**Contract**: `instance set <address>` reads the stored address first. When it differs from the new normalized address, it calls `clearSignIn(location)` after writing the address. Setting the same address again keeps the sign-in.

#### 3. Launch guard

**File**: `tui/src/startup.ts`, `tui/src/cli.tsx`

**Intent**: The interactive TUI never starts in a state where every request would be refused (AC-07).

**Contract**:
- `resolveLaunch` returns `missing` when no address is configured, with the same message as `resolveStartup`.
- `signed_out`, when `readSignIn` yields `null`, carries `"Not signed in to <address>. Run: weles sign-in <email>"`.
- `expired`, when `Date.parse(expiresAt) <= now`, carries `"Your sign-in to <address> has expired. Run: weles sign-in <email>"`.
- Otherwise it returns `ready`.
- `cli.tsx` replaces `resolveStartup` with `resolveLaunch(location, new Date())`, prints the message and exits 1 on any non-ready kind, then calls `setSignInProvider(async () => (await readSignIn(location, address))?.token ?? null)` before `render`.

#### 4. Tests

**File**: `tui/test/launch.test.ts`, `tui/test/authCommand.test.ts`, `tui/test/instanceCommand.test.ts`

**Intent**: Pin AC-06, AC-07 and the binding at the TUI boundary.

**Contract**:
- A successful sign-in command leaves a credential that `readSignIn` returns for the configured address.
- `instance set` to a different address leaves no credential.
- `resolveLaunch` returns `ready` for a sign-in expiring after `now`, `expired` for one expiring at or before `now`, and `signed_out` for none. Fixed ISO literals, no fake timers.

### Success Criteria:

#### Automated Verification:
- Launch and command tests pass: `cd tui && pnpm vitest run test/launch.test.ts test/authCommand.test.ts test/instanceCommand.test.ts`
- Full TUI suite passes: `cd tui && pnpm test`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

#### Manual Verification:
- With the backend running and `weles instance set http://localhost:8000`, run `pnpm --dir tui build && node tui/dist/cli.js sign-in me@x.pl`, then `stat -c %a ~/.config/weles/credentials.json`. The mode is `600`.
- Run `node tui/dist/cli.js`, quit, and run it again. Both launches start without asking to sign in, and the notes list loads.
- Run `node tui/dist/cli.js instance set http://127.0.0.1:8000`, then `node tui/dist/cli.js`. The launch is refused with the `weles sign-in` hint.

---

## Phase 5: Expiry during in-progress work — stubs

### Overview

Materialize the shared expiry code and message.

### Changes Required:

#### 1. Expiry vocabulary

**File**: `tui/src/auth/expiry.ts`

**Intent**: One definition of how the TUI recognizes and words an expired sign-in.

**Contract**:
- `export const SIGN_IN_REQUIRED = "sign_in_required"`
- `export const SIGN_IN_EXPIRED_DETAIL: string`
- `isSignInRequired(code: string): boolean`, with an unimplemented body.

### Success Criteria:

#### Automated Verification:
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 6: Expiry during in-progress work — behavior

### Overview

Tell the person their sign-in expired, keep what is on screen, and let them retry (AC-08).

### Changes Required:

#### 1. Expiry vocabulary

**File**: `tui/src/auth/expiry.ts`

**Intent**: The message names the recovery path.

**Contract**:
- `SIGN_IN_EXPIRED_DETAIL` reads `"Your sign-in has expired. Run \`weles sign-in <email>\` in another terminal, then try again."`
- `isSignInRequired` compares against `SIGN_IN_REQUIRED`.

#### 2. Capture chat store

**File**: `tui/src/store/chat.ts`, `tui/src/api/stream.ts`

**Intent**: An expired sign-in never silently discards the conversation or the draft.

**Contract**:
- In `sendUserMessage` and `approveDraft`, a `SendMessageHttpError` whose code is `sign_in_required` sets `streamError` to `{ code: SIGN_IN_REQUIRED, detail: SIGN_IN_EXPIRED_DETAIL }` and leaves `transcript`, `draft`, and `sessionId` unchanged. Other errors keep today's behaviour.
- `startCaptureSession` throws `SendMessageHttpError` for a coded error body, as `approveNote` already does, so an expiry right after approval surfaces the same message.

#### 3. Sitting store

**File**: `tui/src/store/sitting.ts`

**Intent**: An expired sign-in mid-sitting is explained, and retry resumes the interrupted action.

**Contract**:
- `sittingHttpErrorState` substitutes `SIGN_IN_EXPIRED_DETAIL` for the detail when the code is `sign_in_required`.
- `sittingId`, `cardId`, `front`, `back`, and `lastAction` are preserved.
- `retry()` is unchanged and replays `lastAction`.

#### 4. Tests

**File**: `tui/test/chatSignInExpiry.test.ts`, `tui/test/sittingSignInExpiry.test.ts`

**Intent**: Pin AC-08 in both flows.

**Contract**:
- A `sign_in_required` failure on send keeps the transcript and draft and exposes the expiry detail.
- A `sign_in_required` failure on grade puts the sitting in `error` with the expiry detail and keeps the card.
- A following `retry()`, with the API mock now succeeding, presents the next card.

### Success Criteria:

#### Automated Verification:
- Expiry store tests pass: `cd tui && pnpm vitest run test/chatSignInExpiry.test.ts test/sittingSignInExpiry.test.ts`
- Full TUI suite passes: `cd tui && pnpm test`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

#### Manual Verification:
- Start the backend with `AUTH_SIGN_IN_LIFETIME_HOURS=0.02` (about 70s), sign in, launch the TUI, and exchange one capture message. Wait until the sign-in expires and send another message. The transcript stays, the expiry message appears, and after `weles sign-in` in a second terminal, sending again gets a reply.
- With the same short lifetime, open a review sitting, let the sign-in expire, and grade a card. The expiry message appears with the card still shown. After signing in from a second terminal, retry records the grade and presents the next card.

---

## Testing Strategy

### Unit Tests:

- **Phase 2:**
  - Credential store round trip and file mode on a temp `XDG_CONFIG_HOME`.
  - The request header via `vi.stubGlobal("fetch", …)`, following `tui/test/instanceRouting.test.ts`.
- **Phase 4:**
  - `resolveLaunch` with fixed `now` and `expiresAt` literals.
  - Command tests with `vi.mock("../src/api/auth", …)`, following `tui/test/authCommand.test.ts`.
- **Phase 6:** store tests with `vi.mock` over `src/api/stream` and `src/api/sittings`, keeping the real error classes through `importOriginal`.

### Integration Tests:

None. The backend is unchanged, and the TUI suite doubles only the API module boundary.

### Manual Testing Steps:

1. Sign in, then restart the TUI twice. It is never asked to sign in again (AC-06).
2. Launch with an expired or missing credential. The launch is refused with a hint (AC-07).
3. Let a short-lived sign-in expire mid-capture and mid-sitting. Work stays on screen, and retry after signing in succeeds (AC-08).

## Performance Considerations

Reading `credentials.json` on every request adds one small file read per HTTP call. At the TUI's request rate (15s polling plus user actions) this is negligible, and it buys pick-up of a sign-in made in another terminal.

## Migration Notes

No data or schema migration. Existing installs have no `credentials.json`, so the first launch after upgrading refuses with the `weles sign-in` hint. The token sits in plaintext in a 0600 file, which was chosen over the OS keychain for devcontainer compatibility.

## References

- Effort: `context/efforts/auth-flow/prd.md` (FR-004, FR-005, Open Question 1), `stories.md` (US-03), `roadmap.md` (S-03)
- Research: `context/efforts/auth-flow/research.md` (token storage), `research-domain-tenancy-and-adapter-grain.md`
- Prior slices: `context/archive/changes/2026-09-14-auth-flow-sign-in-gate/plan.md`, `context/archive/changes/2026-09-13-auth-flow-instance-address/plan.md`
- Rules: `context/foundation/testing-conventions.md`
