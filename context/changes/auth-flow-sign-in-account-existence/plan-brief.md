# Sign-In Account-Existence Guard — Plan Brief

> Full plan: `plan.md`

## What & Why

`SignInVerifier.verify()` currently trusts a valid JWT signature alone — it
never checks whether the account it names still exists. Deleting an account
(or wiping the database) leaves every token issued for it accepted until it
naturally expires. This closes that gap: a valid, unexpired token is now also
confirmed against `AccountStore` before it's honored.

## Starting Point

`SignInTokens.verify()` decodes and validates the JWT only; `AccountStore`
exposes `save`/`by_email` but no existence check by id; `compose.py` builds
`SignInTokens` from secret/lifetime alone, with no store access.

## Desired End State

A token that fails signature or expiry validation is still refused for free
(PRD FR-009, unchanged). A token that passes those checks but names a
deleted account is refused with `AccountNoLongerExistsError` (401,
`account_no_longer_exists`) — enforced once at the gate, so every capture,
distill, and remember route inherits it automatically.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Deleted-account error | New `AccountNoLongerExistsError`, mapped to the same 401 | Lets logs/telemetry tell the two refusal causes apart even though the caller sees an opaque 401 either way | Plan (user-confirmed) |
| Store lookup shape | `AccountStore.exists(UserId) -> bool` | Cheapest possible query; no need for a full `Account` at the gate | Plan (user-confirmed) |
| Contract cadence | `SignInTokens` contract parametrized by store kind (in-memory every CI, postgres non-blocking) | Matches `contract-testing.md` and mirrors `AccountStore`'s own suite | Plan (user-confirmed) |
| Per-request DB cost | Accepted as-is, no caching | Single-user instance; a cache would reopen exactly the staleness window this change closes | Plan (user-confirmed) |
| Simulating "account deleted" in tests | Verify a token through a second `SignInTokens` sharing the secret but wired to an empty store | Mirrors the real incident (portable JWT, store-dependent check) with no `AccountStore.delete` feature to build | Plan |

## Scope

**In scope:** `AccountStore.exists`, both its adapters, `SignInTokens.verify()`'s
new guard, the new exception and its HTTP mapping, `compose.py` wiring,
contract and integration test coverage.

**Out of scope:** any account-deletion feature, caching, TUI changes, a
distinguishable HTTP response beyond the `code` field, reopening the archived
`auth-flow-sign-in-gate` frame.

## Architecture / Approach

One TDD'able unit, stubs then behavior. `exists()` and the `verify()` guard
ship together — neither means anything tested in isolation from the other.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Stubs | `AccountStore.exists` signature, both adapter stubs, `AccountNoLongerExistsError`, `SignInTokens` takes `accounts`, narrowed docstrings | Existing `SignInTokens(...)` call sites (test_authenticator.py) need the new required arg |
| 2. Behavior | Real `exists()` on both adapters, the `verify()` guard, compose wiring, error mapping, full test coverage | None significant — small, well-isolated surface |

**Prerequisites:** none — no upstream change blocks this.
**Estimated effort:** small (2 phases, ~7 files touched, ~5 new tests).

## Open Risks & Assumptions

- Assumes no other code path constructs `SignInTokens` without going through
  `compose.py` or the test files this plan updates; grep confirms only
  `test_auth_http.py` and `test_authenticator.py` do so today.

## Success Criteria (Summary)

- A gated route refuses a structurally valid token whose account no longer
  exists, with `account_no_longer_exists` / 401.
- A malformed, altered, foreign-secret, or expired token is still refused
  without touching `AccountStore` (FR-009 unchanged).
- `cd backend && uv run pytest` and `uv run basedpyright` both pass.
