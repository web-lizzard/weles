# Sign-In Account-Existence Guard Implementation Plan

## Overview

A signed, unexpired sign-in token today decodes to a `UserId` on trust alone —
`SignInVerifier.verify()` never asks whether that account still exists. An
operator who deletes an account (or wipes the database) leaves every
previously issued token for it accepted until it naturally expires, up to a
full `SignInLifetime`. This plan closes that gap: a token that fails signature
or expiry validation is still refused with zero database or LLM cost
(PRD FR-009, unchanged), but a token that passes those checks is now confirmed
against `AccountStore` before its `UserId` is returned.

Execution state lives in `todos.md`.

## Current State Analysis

- `SignInVerifier.verify()` (`backend/src/adapters/auth/ports.py:35-51`) documents an
  absolute invariant: "Touches no database, account store, LLM, or network."
  `SignInTokens.verify()` (`backend/src/adapters/auth/tokens.py:35-51`) is the
  sole implementation and only ever decodes and validates the JWT.
- `AccountStore` (`backend/src/adapters/auth/ports.py:6-19`) exposes `save` and
  `by_email` only — no existence check by `UserId`.
- `InMemoryAccountStore` (`backend/src/adapters/auth/in_memory_account_store.py`)
  and `SqlAlchemyAccountStore` (`backend/src/adapters/auth/sqlalchemy_account_store.py`)
  are the port's two implementations, each with a contract suite
  (`backend/tests/unit/auth/contracts/test_account_store_contract.py`) that
  already parametrizes in-memory (every CI) against postgres
  (`pytest.mark.postgres`, non-blocking).
- `backend/src/adapters/auth/compose.py:17-38` builds one `SignInTokens`
  instance from `SigningSecret`/`SignInLifetime` alone, and a separate
  `SqlAlchemyAccountStore(_session_factory)` inline for `_authenticator`.
- `backend/src/adapters/http/errors.py:6-64` is the sole `code -> status`
  mapping table; `CoreException` auto-derives `code` from the class name
  (`context/foundation/rules/exceptions.md`).
- `backend/tests/integration/test_auth_http.py` builds its own
  `InMemoryAccountStore` + `SignInTokens` + `Authenticator` stack
  (`_auth_stack`, lines 31-43) and overrides `get_authenticator` /
  `get_sign_in_verifier` directly — no dependency on `compose.py`'s module
  state.
- `backend/tests/unit/auth/test_authenticator.py:29-38` also constructs a
  `SignInTokens` (as `issuer` only, `verify()` never called) with no
  `AccountStore` argument.

Result: today, a deleted account's tokens stay valid until they expire on
their own — the exact incident this change exists to close.

## Desired End State

- `AccountStore` gains `exists(user_id: UserId) -> bool`, implemented by both
  adapters and covered by the existing contract suite's cadence.
- `SignInTokens.verify()` raises `AccountNoLongerExistsError` (mapped to HTTP
  401, `sign_in_required`'s sibling) when the decoded token's account is gone,
  and still raises nothing-but-CPU `SignInRequiredError` for a malformed,
  altered, foreign-secret, or expired token — the store is never touched on
  that path.
- `compose.py` wires one shared `AccountStore` instance into both the
  authenticator and the verifier.
- Every route behind `require_sign_in` — capture, distill, and remember alike
  — inherits the guard automatically; no route-level change.

Verify with `cd backend && uv run pytest` and `cd backend && uv run basedpyright`.

### Key Discoveries:

- The `SignInVerifier` port docstring (`ports.py:35-44`) states the "touches
  nothing" invariant as absolute; it must be narrowed to "for a token it
  refuses" rather than dropped, since PRD FR-009 and the refused-token path
  still hold it exactly.
- `SqlAlchemyAccountStore.by_email` (`sqlalchemy_account_store.py:29-36`) is
  the pattern for `exists`: one `select(...)`, `scalar_one_or_none()`.
- The cleanest way to prove "account deleted" in the contract suite needs no
  new deletion feature: issue a token from one `SignInTokens` instance
  wired to a populated store, then verify it against a second `SignInTokens`
  sharing the same secret but wired to an *empty* store. This mirrors the
  reported incident (JWT is self-contained and portable; only the
  existence check is store-dependent) without adding an `AccountStore.delete`
  nobody asked for.
- `test_auth_http.py`'s `_auth_stack()` already builds `SignInTokens`
  directly — the natural place for the new "deleted account" HTTP test, using
  a second empty `InMemoryAccountStore` the same way.

## What We're NOT Doing

- No `AccountStore.delete` or any account-deletion feature. The incident was
  a database wipe, not an in-product deletion flow; simulating "account gone"
  in tests uses a second, empty store instance instead (see Key Discoveries).
- No caching of the existence check. Single-user instance, negligible load;
  a cache would reintroduce a staleness window on exactly the path this
  change closes.
- No new HTTP-visible distinction between "malformed token" and "account
  gone" — both still surface as an opaque sign-in refusal to the caller.
  `AccountNoLongerExistsError` exists for internal/log-level differentiation
  only; the response body's `code` differs (`account_no_longer_exists` vs
  `sign_in_required`) but both map to 401 with no further detail.
- No TUI change. The refusal already surfaces through the existing
  `sign_in_required`-family handling (`auth-flow-sign-in-lifetime`); a new
  `code` value needs no new client behavior since the TUI treats any 401 from
  a gated route as "not signed in."
- No change to `Authenticator.sign_in` or `SignInIssuer.issue` — both already
  read the account fresh from the store before issuing.
- Reopening `context/archive/changes/2026-09-14-auth-flow-sign-in-gate`'s
  frame. It is archived; this plan supersedes its "cannot be withdrawn before
  it expires" acceptance in code and docstrings, not by amending that record.

## Implementation Approach

One TDD'able unit — the guard end to end (port method, both adapters, verifier
logic, error mapping, wiring) — as one stubs phase followed by one behavior
phase. The unit is small and load-bearing as a single piece: `exists()` has no
caller other than `verify()`, and `verify()`'s new branch has no meaning
without `exists()`, so splitting them into separate TDD units would pair
stubs that test nothing on their own.

## Phase 1: Account-existence guard — stubs

### Overview

Materialize the symbols Phase 2's tests import, with unimplemented bodies and
updated docstrings. No behavior.

### Changes Required:

#### 1. `AccountStore.exists`

**File**: `backend/src/adapters/auth/ports.py`

**Intent**: Give the verifier a way to ask "is this account still here?"
alongside the existing `by_email` lookup.

**Contract**: `async def exists(self, user_id: UserId) -> bool: ...` added to
the `AccountStore` protocol, with a one-line docstring.

#### 2. Adapter stubs

**File**: `backend/src/adapters/auth/in_memory_account_store.py`,
`backend/src/adapters/auth/sqlalchemy_account_store.py`

**Intent**: Materialize the method on both concrete implementations ahead of
Phase 2's contract tests.

**Contract**: `async def exists(self, user_id: UserId) -> bool: raise NotImplementedError`
on each class.

#### 3. `AccountNoLongerExistsError`

**File**: `backend/src/adapters/auth/exceptions.py`

**Intent**: A distinct, auto-coded `CoreException` for a token whose account
is gone, kept apart from `SignInRequiredError` for internal differentiation
even though both remain an opaque refusal to the caller.

**Contract**: `class AccountNoLongerExistsError(CoreException): pass`, code
auto-derives to `account_no_longer_exists`.

#### 4. `SignInTokens` gains an `AccountStore`

**File**: `backend/src/adapters/auth/tokens.py`

**Intent**: Give `verify()` what Phase 2 needs to check existence, without
changing behavior yet.

**Contract**: `__init__(self, secret: SigningSecret, lifetime: SignInLifetime, accounts: AccountStore) -> None`
stores `self._accounts: AccountStore = accounts`. `verify()` body unchanged.
Update the class docstring: it is no longer unconditionally I/O-free —
narrow the claim to the refused-token path.

#### 5. Port docstring narrowed

**File**: `backend/src/adapters/auth/ports.py`

**Intent**: `SignInVerifier`'s invariant list currently reads as absolute;
narrow it to match the behavior Phase 2 adds.

**Contract**: The "Touches no database, account store, LLM, or network
(PRD FR-009)" bullet gains: this holds for every token `verify()` refuses; a
token that passes signature and expiry is confirmed against `AccountStore`
before its `UserId` is returned, and is refused with
`AccountNoLongerExistsError` when the account is gone.

### Success Criteria:

#### Automated Verification:
- Type check passes: `cd backend && uv run basedpyright`

---

## Phase 2: Account-existence guard — behavior

### Overview

Implement the existence check in both adapters and the verifier's new guard,
wire it through composition, map the new error code, and pin the behavior
with tests.

#### Tests

### Changes Required:

#### 1. `InMemoryAccountStore.exists`

**File**: `backend/src/adapters/auth/in_memory_account_store.py`

**Intent**: Existence by id, under the same lock `save`/`by_email` use.

**Contract**: `async def exists(self, user_id: UserId) -> bool` returns
`True` iff some stored `Account.id == user_id`.

#### 2. `SqlAlchemyAccountStore.exists`

**File**: `backend/src/adapters/auth/sqlalchemy_account_store.py`

**Intent**: One indexed lookup by primary key, same session-per-call shape as
`by_email`.

**Contract**: `select(AuthAccountRow.id).where(AuthAccountRow.id == user_id.value)`,
`scalar_one_or_none() is not None`.

#### 3. `SignInTokens.verify()` guard

**File**: `backend/src/adapters/auth/tokens.py`

**Intent**: A token that decodes and is unexpired is no longer trusted on
signature alone.

**Contract**: After building `UserId` from `sub`, `verify()` calls
`await self._accounts.exists(user_id)`; raises `AccountNoLongerExistsError`
when `False`, otherwise returns `user_id` as before. The existing
`SignInRequiredError` branches (bad signature, malformed payload, expired,
unparseable `sub`) are untouched and still return before any store access.

#### 4. Composition wiring

**File**: `backend/src/adapters/auth/compose.py`

**Intent**: One `AccountStore` instance backs both registration/sign-in and
verification.

**Contract**: `_accounts = SqlAlchemyAccountStore(_session_factory)` built
once; `_sign_in_tokens = SignInTokens(secret=..., lifetime=..., accounts=_accounts)`;
`_authenticator = Authenticator(accounts=_accounts, ...)`.

#### 5. HTTP error mapping

**File**: `backend/src/adapters/http/errors.py`

**Intent**: The new code needs a status like every other `CoreException`
subclass (`context/foundation/rules/exceptions.md`'s exhaustiveness test
enforces this).

**Contract**: `"account_no_longer_exists": 401` added to `EXCEPTION_STATUS_MAP`.

#### 6. Existing call-site fix

**File**: `backend/tests/unit/auth/test_authenticator.py`

**Intent**: `_authenticator()`'s `SignInTokens(...)` construction now requires
`accounts`; it only ever uses the instance as an issuer, so a fresh
`InMemoryAccountStore()` is enough.

**Contract**: `SignInTokens(secret=..., lifetime=..., accounts=InMemoryAccountStore())`.

#### 7. Tests

**File**: `backend/tests/unit/auth/contracts/test_account_store_contract.py`

**Intent**: Pin `exists` on both adapters at the cadence the suite already
uses for `by_email`/`save`.

**Contract**:
- `exists` returns `True` for a saved account's id.
- `exists` returns `False` for an unknown `UserId.new()`.

**File**: `backend/tests/unit/auth/contracts/test_sign_in_tokens_contract.py`

**Intent**: Pin the guard at the port-contract level, store-implementation
agnostic.

**Contract**:
- Extend `_TokenFixture`/`_build_local` to also take an `AccountStore`
  (default: an `InMemoryAccountStore` pre-populated with the issued
  `UserId`, matching `test_verify_returns_the_user_id_a_token_was_issued_for`'s
  existing shape — that test now saves an account first).
- New: `verify` raises `AccountNoLongerExistsError` for a token issued by one
  `SignInTokens` and verified through a second instance sharing the same
  secret and lifetime but wired to an empty `InMemoryAccountStore`.

**File**: `backend/tests/integration/test_auth_http.py`

**Intent**: Pin the guard at the HTTP boundary, through the real gate.

**Contract**: A new test registers and signs in through `auth_http_client`,
then swaps `get_sign_in_verifier`'s override to a second `SignInTokens`
(same secret/lifetime, a fresh empty `InMemoryAccountStore`) before hitting
`/notes` with the original token: 401, `{"code": "account_no_longer_exists"}`.

### Success Criteria:

#### Automated Verification:
- Full backend suite passes: `cd backend && uv run pytest`
- Type check passes: `cd backend && uv run basedpyright`

---

## Testing Strategy

### Unit Tests:
- `test_account_store_contract.py`: `exists` true/false, both adapters,
  postgres marked non-blocking.
- `test_sign_in_tokens_contract.py`: `verify` succeeds when the account
  exists; raises `AccountNoLongerExistsError` when it doesn't, via the
  two-store technique in Key Discoveries.

### Integration Tests:
- `test_auth_http.py`: a gated route refuses a structurally valid,
  unexpired token whose account is no longer in the store, with
  `account_no_longer_exists` / 401.

### Manual Testing Steps:
1. Register and sign in against a local Postgres-backed instance, note the
   token.
2. Delete the account row directly in the database (or point the instance at
   an empty database while keeping the same `AUTH_SIGNING_SECRET`).
3. Call a gated route (`GET /notes`) with the old token: expect 401
   `account_no_longer_exists`, not 200.

## Performance Considerations

Every authenticated request now costs one additional indexed primary-key
lookup at the gate, on top of the JWT decode. Accepted as-is for a
single-user instance; no caching, to avoid reintroducing the staleness
window this change closes.

## Migration Notes

No schema migration — `exists` reads the same `auth_accounts` table
`by_email` already reads. No data migration; existing valid tokens for
existing accounts keep working unchanged.

## References

- Effort: `context/efforts/auth-flow/prd.md` (FR-009)
- Prior slice: `context/archive/changes/2026-09-14-auth-flow-sign-in-gate/frame.md`
  (the "cannot be withdrawn before it expires" acceptance this plan narrows)
- Rules: `context/foundation/rules/exceptions.md`,
  `context/foundation/rules/contract-testing.md`,
  `context/foundation/testing-conventions.md`
