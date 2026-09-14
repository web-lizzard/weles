# Sign-In Gate Implementation Plan

## Overview

Give a Weles instance registration, sign-in, and a deny-by-default gate. A caller without a valid sign-in is refused before any database or LLM work (PRD FR-009), and localhost is gated the same way as a hosted instance. The TUI gains `weles register` and `weles sign-in`. Both confirm the credentials and discard the sign-in, because keeping it is S-03's job. Realizes AC-03, AC-04, AC-05, AC-11, AC-12, AC-13 and PRD FR-009 (`frame.md`, Requirements).

Execution state lives in `todos.md`.

## Current State Analysis

The closed contract session (`discover-contracts-log.md`, commit `66afdae`) put the whole architecture on disk as signatures with `...` bodies:

- `backend/src/domain/shared/identity/model.py`: `UserId`, the only person-shaped value in the core.
- `backend/src/adapters/auth/`:
  - `model.py`: guarded value objects.
  - `ports.py`: `AccountStore`, `SignInIssuer`, `SignInVerifier`.
  - Unimplemented classes: `tokens.py`, `passwords.py`, `authenticator.py`, `in_memory_account_store.py`, `sqlalchemy_account_store.py`.
  - The ORM row in `sqlalchemy_models.py`.
  - `exceptions.py`, `dto.py`, `router.py`, `compose.py`.
- `backend/src/adapters/http/errors.py` already maps every auth code.
- `backend/src/main.py` already mounts capture, notes, and remember under a `gated` router that depends on `require_sign_in`.
- `tui/src/api/auth.ts` and `tui/src/auth/command.ts` hold `declare function` signatures only.

Missing:

- Every method body.
- The `Settings` auth fields.
- The Alembic revision for `auth_accounts`.
- Token and hashing libraries: neither PyJWT nor argon2-cffi is in `backend/pyproject.toml`.
- Contract suites.
- The `cli.tsx` dispatch.
- A no-echo password prompt.

Existing HTTP and BDD suites pass today only because `require_sign_in` has no body. Once it refuses, they go red unless their fixtures override it.

## Desired End State

- `POST /auth/register` creates an account (201) and refuses an invalid email (422), a short password (422), and an already-registered address in any letter case (409).
- `POST /auth/sign-in` returns a bearer token with `expires_at`. It refuses an unknown email, a wrong password, and an unparseable email with the same `invalid_credentials` (401).
- Every capture, notes, and remember route answers 401 `sign_in_required` in the following cases, without touching any store or LLM port:
  - no token
  - a malformed token
  - an altered token
  - a made-up token
  - a token signed with another instance's secret
  - an expired token
- `/health` and non-prod `/_outbox` stay open.
- The instance refuses to start without `AUTH_SIGNING_SECRET` (at least 32 bytes).
- `weles register <email>` and `weles sign-in <email>` prompt for a password without echo, report the outcome, and exit 0, 1, or 2.

Verify with `cd backend && uv run pytest` (with `TEST_DATABASE_URL` for `-m postgres`), `uv run basedpyright`, and `cd tui && pnpm test && pnpm typecheck && pnpm lint`.

### Key Discoveries:

- `backend/src/adapters/auth/router.py:21`: `HTTPBearer(auto_error=False)` makes a missing header fail as `sign_in_required` (401), not as FastAPI's 403.
- `backend/src/main.py:37-40`: deny by default. A router added later is gated unless it is mounted on `app` on purpose.
- `backend/tests/integration/conftest.py`, `backend/tests/bdd/conftest.py` and `backend/tests/integration/test_capture_http.py` are the only modules that build `TestClient(main.app)`. Each needs `app.dependency_overrides[require_sign_in]`.
- `backend/tests/conftest.py:20-24`: `pytest_configure` `setdefault`s env for an offline suite. The test-only signing secret goes there.
- `backend/tests/unit/distill/contracts/test_card_repository_contract.py:103-117`: the contract-suite shape to follow is a `params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]` fixture plus a `_Committing…` wrapper.
- `backend/src/adapters/out/sqlalchemy/migrations/versions/c24cb831e287_create_remember_tables.py`: the current Alembic head, and the style reference for the new revision.
- `backend/tests/unit/test_settings.py::test_settings_defaults_distill_model_when_unset` is red before this change. The user's uncommitted `settings.py` model edit, plus a `.env` override, change the default it asserts.
- `tui/src/api/instance.ts:34`: `getClient()` is the memoized `openapi-fetch` client. `tui/test/instanceCommand.test.ts` is the command-test pattern (injected `out`/`err`, temp `XDG_CONFIG_HOME`).
- No maintained Python token library has a native async signing API. Async JWT packages either fetch JWKS over the network (ruled out by FR-009) or wrap sync PyJWT inside a framework integration.

## What We're NOT Doing

- Handing `UserId` to any capture, distill, or remember handler (S-04, S-05).
- Separating data between people (S-04, S-05).
- The TUI keeping, sending, or guarding on a sign-in, and the TUI half of instance binding (S-03).
- Signing out (S-06), attempt limits or hashing-cost protection (S-07).
- Early invalidation of a still-valid sign-in, revocation, refresh tokens.
- Password reset, email verification, registration gating, and every other PRD Non-Goal.
- Gating `/health` or `/_outbox`.
- Acceptance scenarios. The `/bdd` lane authors them against this interface, and they are not phases of this plan.

## Implementation Approach

Build from the inside out. Every unit already has its signature, so each phase fills bodies behind tests written first:

1. Value objects and hashing.
2. Tokens.
3. Stores and migration.
4. Orchestration.
5. HTTP wiring and the gate, which is the phase that flips the existing suites and so also carries their overrides.
6. The TUI API module.
7. The TUI commands.

`SignInTokens` keeps its `async` methods to satisfy the ports and calls PyJWT synchronously inside them. HS256 signing is microseconds of CPU with no I/O, so offloading to a thread would cost more than the work itself. `PasswordHasher` does offload Argon2id through `asyncio.to_thread`, because it is deliberately slow.

## Critical Implementation Details

`SignInTokens.verify` must pin `algorithms=["HS256"]` and require the `exp` and `sub` claims. Otherwise a token with `alg: none`, or one without an expiry, can pass.

Phase 5 turns `require_sign_in` from a no-op into a refusal. The override fixtures must land in the same phase, or every existing HTTP and BDD test goes red at once.

`get_sign_in_verifier` and the authenticator's issuer must be the same process-wide `SignInTokens` instance, built once from `Settings`.

## Phase 1: Auth value objects and password hashing

### Overview

Fill the bodies of the auth adapter's value objects and the password hasher: the pure rules registration and sign-in stand on.

### Changes Required:

#### 1. Value object behaviour

**File**: `backend/src/adapters/auth/model.py`

**Intent**: Make email identity, the password minimum, and account creation real, so AC-05's "same person" and the operator-raisable floor of 8 hold.

**Contract**:
- `EmailAddress.parse(raw)` validates with Pydantic's `EmailStr` rules, then case-folds the whole address and strips surrounding whitespace. Invalid syntax raises `InvalidEmailAddressError`.
- `PasswordPolicy.admit(password)` raises `PasswordTooShortError` when `len(secret) < min_length`.
- `Account.register(email, password_hash)` returns a fresh `UserId.new()` and `created_at=datetime.now(UTC)`.

#### 2. Password hasher

**File**: `backend/src/adapters/auth/passwords.py`, `backend/pyproject.toml`, `backend/uv.lock`

**Intent**: Salted, slow hashing that never blocks the event loop.

**Contract**:
- Add the `argon2-cffi` dependency.
- `PasswordHasher.hash` runs `argon2.PasswordHasher().hash` through `asyncio.to_thread` and returns a `PasswordHash`.
- `verify` returns `False` on a mismatch or an unparseable hash, and never raises for a wrong password.

### Success Criteria:

#### Automated Verification:
- Auth model and hasher unit tests pass: `cd backend && uv run pytest tests/unit/auth -v`
- Type check passes: `cd backend && uv run basedpyright`

---

## Phase 2: Sign-in tokens and the token port contract

### Overview

Implement `SignInTokens` on PyJWT HS256, and prove both token ports against one contract suite.

### Changes Required:

#### 1. Token implementation

**File**: `backend/src/adapters/auth/tokens.py`, `backend/pyproject.toml`, `backend/uv.lock`

**Intent**: Issue sign-ins only this instance accepts, and verify them with no lookup (FR-009).

**Contract**:
- Add the `pyjwt` dependency.
- `issue(user_id)` encodes `{"sub": str(user_id.value), "exp": now + lifetime}` with HS256 over `SigningSecret` and returns `IssuedSignIn(token, user_id, expires_at)`.
- `verify(token)` decodes with `algorithms=["HS256"]` and `options={"require": ["exp", "sub"]}`.
- Every `jwt.PyJWTError`, and a `sub` that is not a UUID, raise `SignInRequiredError` with no distinguishing message.
- No I/O in either method.

#### 2. Token contract suite

**File**: `backend/tests/unit/auth/contracts/test_sign_in_tokens_contract.py`

**Intent**: One suite over the `SignInIssuer` and `SignInVerifier` implementations (`ids=["local"]`), per `context/foundation/rules/contract-testing.md`.

**Contract**:
- A token round-trips to the `UserId` it was issued for.
- The following tokens are all refused with `SignInRequiredError`:
  - a token signed with a different `SigningSecret`
  - a token with any altered character
  - a made-up string
  - a token past its lifetime
- Expiry is proven without frozen time: lifetime is constructor input.

### Success Criteria:

#### Automated Verification:
- Token contract passes: `cd backend && uv run pytest tests/unit/auth/contracts/test_sign_in_tokens_contract.py -v`
- Type check passes: `cd backend && uv run basedpyright`

---

## Phase 3: Account stores and the auth_accounts migration

### Overview

Give `AccountStore` its in-memory and Postgres implementations, the Alembic revision, and one contract suite run over both.

### Changes Required:

#### 1. In-memory store

**File**: `backend/src/adapters/auth/in_memory_account_store.py`

**Intent**: The store acceptance and unit tests run on, with the same uniqueness guarantee as Postgres.

**Contract**:
- A dict keyed by `EmailAddress`, guarded by an `asyncio.Lock`.
- `save` raises `EmailAlreadyRegisteredError` when a different account id already holds the email. Re-saving the same account replaces it.
- `by_email` returns the account or `None`.

#### 2. Postgres store

**File**: `backend/src/adapters/auth/sqlalchemy_account_store.py`

**Intent**: Durable accounts, where the unique constraint, not a pre-check, enforces uniqueness.

**Contract**:
- Each `save` opens its own session, merges an `AuthAccountRow`, and commits.
- An `IntegrityError` on the `email` unique constraint becomes `EmailAlreadyRegisteredError`.
- `by_email` selects by `email == EmailAddress.value` and maps the row back to `Account`.

#### 3. Migration

**File**: `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_create_auth_accounts.py`

**Intent**: Its own Alembic revision for the new table (roadmap S-01).

**Contract**:
- `down_revision = "c24cb831e287"`.
- Creates `auth_accounts` (`id` UUID pk, `email` unique not null, `password_hash` not null, `created_at` timestamptz not null) with `op.f` constraint names.
- `downgrade` drops it.

#### 4. AccountStore contract suite

**File**: `backend/tests/unit/auth/contracts/test_account_store_contract.py`

**Intent**: One behavioural suite parametrized `in_memory` and `postgres` (marked `postgres`).

**Contract**:
- A saved account is found by an equal `EmailAddress`.
- An unknown email yields `None`.
- A second account with the same canonical email raises `EmailAlreadyRegisteredError`.

### Success Criteria:

#### Automated Verification:
- In-memory contract passes: `cd backend && uv run pytest tests/unit/auth/contracts/test_account_store_contract.py -m "not postgres" -v`
- Postgres contract passes: `cd backend && uv run pytest tests/unit/auth/contracts/test_account_store_contract.py -m postgres -v`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- Run `cd backend && uv run alembic upgrade head`, then `uv run alembic downgrade -1`, then `uv run alembic upgrade head` against the dev database. All three steps succeed and `auth_accounts` exists at the end.

---

## Phase 4: Authenticator

### Overview

Fill `Authenticator.register` and `sign_in`, the orchestration the router calls.

### Changes Required:

#### 1. Registration and sign-in orchestration

**File**: `backend/src/adapters/auth/authenticator.py`

**Intent**: Register a person without issuing a sign-in (AC-03), and refuse unknown and wrong credentials alike (AC-04).

**Contract**:
- `register`: `policy.admit` runs before any hashing, then `passwords.hash`, then `Account.register`, then `accounts.save`. Returns the new `UserId`.
- `sign_in`: `accounts.by_email`. `None` or `passwords.verify == False` raises `InvalidCredentialsError`. Otherwise it returns `issuer.issue(account.id)`.

### Success Criteria:

#### Automated Verification:
- Authenticator unit tests pass on `InMemoryAccountStore` and a real `SignInTokens`: `cd backend && uv run pytest tests/unit/auth/test_authenticator.py -v`
- Type check passes: `cd backend && uv run basedpyright`

---

## Phase 5: HTTP endpoints, sign-in gate, and wiring

### Overview

Wire settings and composition, fill the router and the gate, and keep every existing HTTP and BDD suite green behind the now-active gate.

### Changes Required:

#### 1. Settings

**File**: `backend/src/config/settings.py`, `backend/tests/conftest.py`, `backend/tests/unit/test_settings.py`

**Intent**: Per-instance auth configuration with no shipped secret. The file's pending model-name edit is committed in this phase by the user's choice.

**Contract**:
- `auth_signing_secret: SecretStr` (required, no default).
- `auth_sign_in_lifetime_hours: float = 24.0`.
- `auth_password_min_length: int = 8`.
- `pytest_configure` `setdefault`s `AUTH_SIGNING_SECRET` to a test-only value of at least 32 bytes.
- `test_settings_defaults_distill_model_when_unset` is aligned with the committed default and isolated from `.env`, the way `test_settings_raises_when_database_url_missing` is.
- A settings test asserts construction fails without the secret.

#### 2. Composition

**File**: `backend/src/adapters/auth/compose.py`

**Intent**: One process-wide `SignInTokens` shared by issuer and verifier, and an authenticator on Postgres.

**Contract**:
- Module-level singletons are built from `Settings()`, following `backend/src/adapters/compose.py`.
- `SigningSecret` and `SignInLifetime(timedelta(hours=…))` construct one `SignInTokens`.
- `get_authenticator` combines `SqlAlchemyAccountStore` (session factory from `adapters/out/sqlalchemy/engine.py`), `PasswordHasher`, `PasswordPolicy` and that tokens instance.
- `get_sign_in_verifier` returns the same tokens instance.

#### 3. Router and gate

**File**: `backend/src/adapters/auth/router.py`

**Intent**: The two public endpoints and the gate, as the docstrings on disk describe.

**Contract**:
- `require_sign_in`: `credentials is None` raises `SignInRequiredError`. Otherwise it returns `await verifier.verify(credentials.credentials)`.
- `register` parses the email (invalid raises `InvalidEmailAddressError`) and returns `RegisterResponseDTO(user_id)` with 201.
- `sign_in` maps an `InvalidEmailAddressError` from parsing to `InvalidCredentialsError`, and returns `SignInResponseDTO(access_token, expires_at)`.

#### 4. Existing suites behind the gate

**File**: `backend/tests/integration/conftest.py`, `backend/tests/bdd/conftest.py`, `backend/tests/integration/test_capture_http.py`

**Intent**: Suites about capture, notes, and remember keep testing those, not the gate.

**Contract**: Every fixture that builds `TestClient(app)` for a gated router also sets `app.dependency_overrides[require_sign_in] = lambda: UserId.new()`. Clearing `dependency_overrides` at teardown stays as it is.

#### 5. Auth HTTP tests

**File**: `backend/tests/integration/test_auth_http.py`

**Intent**: Request-to-response contracts for registration, sign-in, and the gate.

**Contract**:
- A module-private fixture overrides `get_authenticator` with an in-memory `Authenticator` and `get_sign_in_verifier` with its tokens instance.
- Register, then sign-in, yields a token, and that token passes a gated route.
- Duplicate registration in a different case yields 409 `email_already_registered`.
- A wrong password and an unknown email both yield 401 `invalid_credentials`.
- A gated route without a token, or with a forged token, yields 401 `sign_in_required`, while its store and LLM dependencies are overridden with `_Fake…` doubles that fail the test if touched (FR-009).
- `/health` answers 200 without a token.

### Success Criteria:

#### Automated Verification:
- Full backend suite passes: `cd backend && uv run pytest -m "not postgres"`
- Postgres lane passes: `cd backend && uv run pytest -m postgres`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- With `AUTH_SIGNING_SECRET` set in `backend/.env`, start the backend, then run `curl -i localhost:8000/notes`. The response is 401 `sign_in_required`.
- `curl -i -X POST localhost:8000/auth/register -H 'Content-Type: application/json' -d '{"email":"a@x.pl","password":"longenough"}'` returns 201.
- Signing in with the same body at `/auth/sign-in` returns a token.
- `curl -i localhost:8000/notes -H "Authorization: Bearer <token>"` returns 200.
- Start the backend with `AUTH_SIGNING_SECRET` unset. It refuses to start.

---

## Phase 6: TUI auth API module

### Overview

Regenerate the API types and implement `register` and `signIn` as discriminated outcomes.

### Changes Required:

#### 1. Generated schema

**File**: `tui/src/api/generated/schema.d.ts`

**Intent**: Type the new `/auth/register` and `/auth/sign-in` paths.

**Contract**: The output of `pnpm generate:api` against the Phase 5 backend.

#### 2. API functions

**File**: `tui/src/api/auth.ts`

**Intent**: Refusals the backend states by code become outcomes. The token never leaves this module until S-03.

**Contract**:
- `register` POSTs through `getClient()`. 201 maps to `registered`. `email_already_registered`, `invalid_email_address`, and `password_too_short` map to their outcomes.
- `signIn` maps 200 to `{kind: "signed_in", expiresAt}` and drops `access_token`. `invalid_credentials` maps to its outcome.
- Transport failures and other statuses throw.

### Success Criteria:

#### Automated Verification:
- Regenerate the schema against the running backend: `cd tui && pnpm generate:api`
- TUI auth API tests pass: `cd tui && pnpm vitest run test/auth.test.ts`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 7: TUI register and sign-in commands

### Overview

Implement the two commands, a no-echo password prompt, and their dispatch from the CLI entry.

### Changes Required:

#### 1. Commands

**File**: `tui/src/auth/command.ts`

**Intent**: Register and sign in from the terminal, without the password ever touching argv or piped stdin.

**Contract**:
- `args.length !== 1` prints usage and returns 2.
- An unconfigured instance prints the `resolveStartup` message and returns 1 before any prompt.
- Otherwise it calls `setInstanceAddress`, then `readSecret("Password: ")`, then the API call.
- `registered` and `signed_in` print a confirmation and return 0.
- `already_registered` tells the person to sign in instead and returns 1.
- `invalid_email`, `password_too_short`, and `invalid_credentials` print a refusal and return 1. The `invalid_credentials` message never says which field was wrong.

#### 2. No-echo prompt and dispatch

**File**: `tui/src/auth/readSecret.ts`, `tui/src/cli.tsx`

**Intent**: Thin glue that connects the commands to the real terminal.

**Contract**:
- `readSecret` rejects when `process.stdin.isTTY` is false (the command maps that to exit 1). Otherwise it reads a line from stdin in raw mode without echoing.
- `cli.tsx` adds `register` and `sign-in` to `commands` and to the help text, and dispatches to `runRegisterCommand` and `runSignInCommand` with `{location, readSecret, out, err}`, then calls `process.exit(code)`.

### Success Criteria:

#### Automated Verification:
- TUI auth command tests pass: `cd tui && pnpm vitest run test/authCommand.test.ts`
- Full TUI suite passes: `cd tui && pnpm test`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

#### Manual Verification:
- With the backend running and `weles instance set http://localhost:8000`, run `pnpm --dir tui build && node tui/dist/cli.js register me@x.pl`. The password is not echoed and the command reports registration.
- `node tui/dist/cli.js sign-in ME@x.pl` with the right password reports a successful sign-in and exits 0. With a wrong password it exits 1 without naming the field.
- `echo pw | node tui/dist/cli.js sign-in me@x.pl` exits 1 without sending a request.

---

## Testing Strategy

### Unit Tests:

- Phases 1-4:
  - value-object rules
  - hash and verify
  - token and account-store contract suites under `backend/tests/unit/auth/contracts/`
  - authenticator orchestration on in-memory adapters and real hashing and tokens
- Phases 6-7: vitest with `vi.mock` over `src/api/auth` for commands, and `fetch` stubbed for the API module.

### Integration Tests:

- Phase 5: `backend/tests/integration/test_auth_http.py` over `main.app` with in-memory auth composition.
- Phase 3: the `postgres` lane runs the `AccountStore` contract against a migrated database.

### Manual Testing Steps:

1. Start the backend with a generated `AUTH_SIGNING_SECRET` in `backend/.env`.
2. Register and sign in with curl, then call a gated route with and without the token.
3. Register and sign in through `weles register` and `weles sign-in`.

Acceptance scenarios for AC-03..05, AC-11..13 and FR-009 come from `/bdd auth-flow-sign-in-gate`.

## Performance Considerations

Gate refusal costs one HS256 verification and no I/O. Argon2id hashing runs off the event loop but is unlimited per attempt until S-07. This is accepted in `frame.md`, since no instance is deployed.

## Migration Notes

A new, additive `auth_accounts` table with no data backfill (PRD Non-Goals: every instance starts empty). Every operator must set `AUTH_SIGNING_SECRET` (for example `openssl rand -hex 32`) before starting an instance. The TUI's capture, notes, and remember calls are refused until S-03 (accepted in `frame.md`).

## References

- Frame: `context/changes/auth-flow-sign-in-gate/frame.md`, `frame-log.md`
- Contracts: `context/changes/auth-flow-sign-in-gate/discover-contracts-log.md`, commit `66afdae`
- Effort: `context/efforts/auth-flow/prd.md` (FR-009), `stories.md` (US-02, US-05), `roadmap.md` (S-01)
- Rules: `context/foundation/rules/contract-testing.md`, `exceptions.md`, `layering.md`; `context/foundation/testing-conventions.md`
