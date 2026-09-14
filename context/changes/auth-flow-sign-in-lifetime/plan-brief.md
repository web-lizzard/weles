# Sign-In Lifetime — Plan Brief

> Full plan: `plan.md`

## What & Why

Since S-01, the backend refuses every TUI data request, because the TUI neither keeps nor sends a sign-in. This change makes the TUI remember a sign-in across restarts, send it only to the instance that issued it, and handle expiry without losing in-progress capture or review work (AC-06, AC-07, AC-08).

## Starting Point

- **Backend:** issues 24h HS256 sign-ins and answers 401 `sign_in_required` to anything else.
- **TUI:** `weles sign-in` confirms the credentials and discards the token. Startup checks only that an address is configured.

## Desired End State

- `weles sign-in` stores a 0600 credential pinned to the configured address.
- The TUI launches straight in while that credential is valid, and refuses with a `weles sign-in` hint when it is missing, foreign, or expired.
- Every request carries the bearer token.
- Expiry mid-capture or mid-sitting keeps the work on screen and explains how to sign in again and retry.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Storage | Separate `credentials.json`, mode 0600 | No native dependency, works in the devcontainer, and keeps the secret apart from the address | Plan |
| Instance binding | One sign-in, pinned to its address; switching clears it | Directly enforces "one instance at a time" and never leaks a token to another instance | Roadmap / Plan |
| Expiry mid-work | Message plus retry after `weles sign-in` in another terminal | Nothing is lost, there is no Ink raw-mode conflict, and the existing sitting `retry` is reused | Plan |
| Token freshness | Read from disk on every request | A sign-in made in another terminal takes effect without a restart | Plan |
| Launch guard | Local `expiresAt` check before rendering | An expired sign-in is caught before the first refused request | Plan |
| Lifetime | Keep the 24h default | User's choice, over the PRD's "a few days"; operators can raise it | Plan |
| In-TUI sign-in prompt | Not built; no slice owns it yet | A follow-up for `/roadmap auth-flow` | Plan |

## Scope

**In scope:**
- Credential store.
- Bearer header on client and stream requests.
- Sign-in command persistence.
- Clearing on instance switch.
- Launch guard.
- Expiry handling in the chat and sitting stores.

**Out of scope:**
- Backend changes.
- In-TUI sign-in.
- OS keychain.
- Multiple instances.
- Sign-out (S-06) and attempt limits (S-07).
- Expiry messaging for the notes and due polling.
- BDD, since there is no node-side lane.

## Architecture / Approach

```
weles sign-in ─► api/auth.signIn ─► credentialStore.writeSignIn (0600, pinned address)
weles instance set <other> ─► credentialStore.clearSignIn
weles ─► resolveLaunch(now) ─► ready? ─► setSignInProvider(readSignIn) ─► render
every request ─► onRequest middleware / authorizationHeaders() ─► Bearer <token>
401 sign_in_required ─► chat/sitting store ─► SIGN_IN_EXPIRED_DETAIL, work kept, retry
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Keep and send — stubs | Credential store and provider signatures | — |
| 2. Keep and send — behavior | 0600 store, Bearer on both request paths | `writeFile` mode ignored on an existing file |
| 3. Persist and guard — stubs | Widened `SignInOutcome`, `resolveLaunch` | — |
| 4. Persist and guard — behavior | Stored sign-in, switch clears, launch refusal | `cli.tsx` wiring order (provider before render) |
| 5. Expiry mid-work — stubs | Shared expiry code and message | — |
| 6. Expiry mid-work — behavior | Chat keeps draft, sitting retry after sign-in | Chat's clear-draft-on-error default |

**Prerequisites:** A running backend with `AUTH_SIGNING_SECRET` set for the manual checks, and a short `AUTH_SIGN_IN_LIFETIME_HOURS` for the expiry checks.
**Estimated effort:** 6 small phases, about one session of `/unit-test` → `/implement` cycles.

## Open Risks & Assumptions

- The token sits in plaintext, protected only by file mode. This was accepted over the keychain.
- 24h is shorter than the PRD's "a few days". This was chosen deliberately.
- The notes list and due count show generic failure or stale state after expiry until the next launch or retry.

## Success Criteria (Summary)

- `cd tui && pnpm test && pnpm typecheck && pnpm lint` passes.
- Restarting the TUI keeps the person signed in, and an expired or missing sign-in blocks the launch with a hint.
- Expiry mid-capture or mid-sitting keeps the work on screen, and retry succeeds after signing in again.
