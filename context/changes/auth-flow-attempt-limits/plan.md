# Attempt Limits Implementation Plan

## Overview

Limit repeated sign-in and registration attempts from one source (roadmap S-07, PRD FR-010, AC-18, AC-19, AC-20). Today an attacker who learns an instance's address can guess passwords and register accounts as fast as the instance answers, and every attempt costs an Argon2 hash. This change resolves PRD Open Question 2. After 5 failed sign-ins in 15 minutes, a source's further sign-ins are refused until the window moves on. After 10 registrations in an hour, its further registrations are refused the same way. An operator can change both limits. A refusal is HTTP 429 `too_many_attempts` with `Retry-After`, and the TUI tells the person how long to wait.

Execution state lives in `todos.md`, per the `todos.md` format reference.

## Current State Analysis

- S-01 left a self-contained auth adapter in `backend/src/adapters/auth/`: `Authenticator` (register, sign-in), `AccountStore` with in-memory and SQLAlchemy implementations, `SignInTokens`, and the router at `/auth`.
- Nothing counts attempts. `Authenticator.sign_in` goes straight to `accounts.by_email` and Argon2 verification (`backend/src/adapters/auth/authenticator.py:43-54`). `register` hashes before saving (`authenticator.py:31-41`).
- The router does not know about the request's origin (`backend/src/adapters/auth/router.py:48-76`).
- The hosted instance runs behind the Mikrus edge, which terminates TLS and forwards plain HTTP (`context/efforts/deployment/research.md:36-40`). The app's direct peer is therefore the proxy, not the client.
- The TUI maps only coded refusals it knows. Any other status throws `signIn failed: <status>` (`tui/src/api/auth.ts:44-83`).

## Desired End State

- `POST /auth/sign-in` answers 429 `too_many_attempts` with a `Retry-After` header to a source that has 5 failed sign-ins within the last 15 minutes. This happens even when the credentials are correct, and before any account lookup or password hashing.
- A successful sign-in clears that source's failures.
- `POST /auth/register` answers 429 the same way to a source's 11th registration attempt within an hour, before any hashing or saving.
- A different source is never refused because of another source's attempts.
- A source is the connection's peer address. When, and only when, that peer is listed in `AUTH_TRUSTED_PROXY_ADDRESSES`, the source is the rightmost `X-Forwarded-For` entry that is not itself a trusted proxy.
- Counters live behind an `AttemptLedger` port with in-memory and Postgres adapters, and one contract suite runs over both. They survive restarts on Postgres.
- `weles sign-in` and `weles register` print `Too many attempts. Try again in about N minutes.` and exit 1.

Verify with the full backend suite (both lanes), basedpyright, the TUI suite, typecheck, and lint, plus the curl and TUI recipes in Phases 6 and 8.

### Key Discoveries:

- Auth has no domain or application layer. Ports, models, and both store implementations sit side by side in `adapters/auth/` (`in_memory_account_store.py`, `sqlalchemy_account_store.py`). The ledger follows that layout, not `adapters/out/in_memory/`.
- Per-instance configuration is constructor input, never a method argument, and is validated on construction (`SignInTokens`, `SignInLifetime` in `backend/src/adapters/auth/model.py:108-133`). `AttemptLimits` follows the same rule.
- Time-based contract tests use a tiny configured period instead of a clock (`tests/unit/auth/contracts/test_sign_in_tokens_contract.py:80-84`). The ledger's window test does the same.
- `errors.py` must not import concrete exception classes (`context/foundation/rules/exceptions.md`). The exhaustiveness test fails as soon as a new `CoreException` subclass lacks a map entry, so the map entries land in the same phase as the exceptions.
- The Postgres `engine` fixture truncates every public table after each test (`tests/integration/support/postgres.py:93-114`), so a new table needs no extra cleanup.
- An uncommitted S-04 migration `d52a781c5827` already sits on top of `d4e8f1a29b3c_create_auth_accounts`.
- `TestClient` reports peer host `testclient`. HTTP tests exercise the trusted-proxy path by overriding the trusted-proxy provider with `["testclient"]` and sending `X-Forwarded-For`.

## What We're NOT Doing

- Acceptance scenarios for AC-18, AC-19, and AC-20. They come from the `/bdd` lane.
- Configuring the proxy or `AUTH_TRUSTED_PROXY_ADDRESSES` on the hosted instance. That belongs to the `deployment` effort.
- Locking an account after failures from many sources, CAPTCHA, or progressive delays.
- Volumetric flooding and DDoS protection (PRD Non-Goals).
- Limiting gated capture, notes, or remember routes.
- Atomic check-and-record. A concurrent burst may overshoot a limit by its degree of parallelism.
- Regenerating the TUI OpenAPI schema. The 429 body is read through the existing untyped `errorCode` path.

## Implementation Approach

The work goes inside-out: port and adapters, then `Authenticator`, then HTTP and settings, then the TUI. Every TDD'able unit is split into a stubs phase and a behavior phase. Each stubs phase keeps the current behavior, so the existing suites stay green. New parameters are accepted and threaded through, but not yet acted on.

- **Ledger.** `AttemptLedger` exposes `ensure_allowed`, `record`, and `clear`. It counts attempts in a sliding window per `(action, source)`.
- **Sign-in.** `Authenticator` checks the ledger before the account lookup, records a failure, and clears the source on success.
- **Registration.** `Authenticator` checks the ledger and records the attempt before hashing, so every attempt that reaches it counts.
- **Source and headers.** A pure `resolve_attempt_source` decides the source. The HTTP error handler adds `Retry-After` from the exception's `retry_after_seconds` attribute.

## Critical Implementation Details

The new migration's `down_revision` is whichever revision is the single Alembic head when Phase 2 runs. Today that is `d52a781c5827` if S-04's migration has been committed, and `d4e8f1a29b3c` if it has not. Check the `down_revision` chain under `migrations/versions/` before writing it, or the migration will branch.

---

## Phase 1: Attempt ledger — stubs

### Overview

Materialize the ledger's port, value objects, exceptions, and both adapter shells, so Phase 2's contract suite can import them.

### Changes Required:

#### 1. Value objects

**File**: `backend/src/adapters/auth/model.py`

**Intent**: Name what is counted and the limit each kind of attempt is held to, as validated per-instance configuration.

**Contract**:
- `AttemptAction(StrEnum)`: `SIGN_IN = "sign_in"`, `REGISTRATION = "registration"`.
- `AttemptSource(BaseModel, frozen)`: `value: str`.
- `AttemptLimit(BaseModel, frozen)`: `max_attempts: int`, `window: timedelta`. Construction raises `NonPositiveAttemptLimitError` when `max_attempts < 1` or `window <= 0`.
- `AttemptLimits(BaseModel, frozen)`: `sign_in: AttemptLimit`, `registration: AttemptLimit`, plus `for_action(action: AttemptAction) -> AttemptLimit`.
- `DEFAULT_ATTEMPT_LIMITS`: `sign_in` is 5 in 15 minutes, `registration` is 10 in 60 minutes.

#### 2. Exceptions and status mapping

**File**: `backend/src/adapters/auth/exceptions.py`, `backend/src/adapters/http/errors.py`

**Intent**: Give the refusal and the configuration error their codes, and keep the exhaustiveness test green.

**Contract**:
- `TooManyAttemptsError(CoreException)`: constructor `(retry_after_seconds: int)`, stored as the public attribute `retry_after_seconds`. There are no message args, so `str()` stays `too many attempts`.
- `NonPositiveAttemptLimitError(CoreException)`.
- The map gains `"too_many_attempts": 429` and `"non_positive_attempt_limit": 500`.

#### 3. Port

**File**: `backend/src/adapters/auth/ports.py`

**Intent**: One boundary for counting attempts, with invariants every implementation holds.

**Contract**: `AttemptLedger(Protocol)`:
- `async ensure_allowed(action: AttemptAction, source: AttemptSource) -> None` raises `TooManyAttemptsError` when the source already has `max_attempts` attempts of that action within the window. `retry_after_seconds` is the whole seconds, rounded up and at least 1, until the oldest counted attempt leaves the window.
- `async record(action, source) -> None` counts one attempt now.
- `async clear(action, source) -> None` forgets that source's attempts of that action.
- Invariants: attempts of one action or source never count toward another, and limits are constructor input.

#### 4. Adapter shells

**File**: `backend/src/adapters/auth/in_memory_attempt_ledger.py`, `backend/src/adapters/auth/sqlalchemy_attempt_ledger.py`, `backend/src/adapters/auth/sqlalchemy_models.py`

**Intent**: Importable implementations with unimplemented bodies, plus the row model the migration will create.

**Contract**:
- `InMemoryAttemptLedger(limits: AttemptLimits)`.
- `SqlAlchemyAttemptLedger(session_factory: async_sessionmaker[AsyncSession], limits: AttemptLimits)`.
- Method bodies raise `NotImplementedError`.
- `AuthAttemptRow`, table `auth_attempts`: `id` UUID primary key, `action` String not null, `source` String not null, `attempted_at` timestamptz not null, and an index on `(action, source, attempted_at)`.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd backend && uv run basedpyright`.
- The existing backend suite, including the exception exhaustiveness test, still passes: `cd backend && uv run pytest -m "not postgres"`.

---

## Phase 2: Attempt ledger — behavior

### Overview

Fill both ledgers behind one contract suite, and create the `auth_attempts` table.

### Changes Required:

#### 1. Contract suite

**File**: `backend/tests/unit/auth/contracts/test_attempt_ledger_contract.py`

**Intent**: Pin the port's behavior once, for both adapters.

**Contract**:
- A fixture is parametrized as `in_memory` plus `postgres` with `pytest.mark.postgres`, the same shape as `test_account_store_contract.py`.
- Tests:
  - allowed below the limit;
  - refused at the limit with a positive `retry_after_seconds`;
  - `clear` lets the source through again;
  - another source and another action are unaffected;
  - attempts older than the window stop counting. This test uses `window=timedelta(milliseconds=1)` and a short `asyncio.sleep`, with no clock.

#### 2. In-memory ledger

**File**: `backend/src/adapters/auth/in_memory_attempt_ledger.py`

**Intent**: Per-`(action, source)` timestamps guarded by an `asyncio.Lock`, pruned to the window on every call.

**Contract**: As the port.

#### 3. Postgres ledger

**File**: `backend/src/adapters/auth/sqlalchemy_attempt_ledger.py`

**Intent**: Count and record attempts in `auth_attempts`, one session and commit per call, like `SqlAlchemyAccountStore`.

**Contract**:
- `ensure_allowed` counts rows with `attempted_at` inside the window and reads the oldest of them.
- `record` inserts a row and, in the same transaction, deletes that key's rows older than the window, so the table stays bounded.
- `clear` deletes the key's rows.

#### 4. Migration

**File**: `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_create_auth_attempts.py`

**Intent**: Create `auth_attempts` and its index. Downgrade drops both.

**Contract**: `down_revision` is the current single head (see Critical Implementation Details).

### Success Criteria:

#### Automated Verification:

- The attempt ledger contract passes in memory: `cd backend && uv run pytest tests/unit/auth/contracts/test_attempt_ledger_contract.py -m "not postgres" -v`.
- The attempt ledger contract passes on Postgres: `cd backend && uv run pytest tests/unit/auth/contracts/test_attempt_ledger_contract.py -m postgres -v`.
- The full backend suite passes: `cd backend && uv run pytest`.
- Type check passes: `cd backend && uv run basedpyright`.

#### Manual Verification:

- `cd backend && uv run alembic upgrade head`, then `\d auth_attempts` in `psql`, shows the table and its `(action, source, attempted_at)` index.

---

## Phase 3: Limits in the authenticator — stubs

### Overview

Thread a ledger and a source through `Authenticator` and every call site, with no limiting yet.

### Changes Required:

#### 1. Authenticator signature

**File**: `backend/src/adapters/auth/authenticator.py`

**Intent**: Give registration and sign-in what they need to limit attempts.

**Contract**:
- `Authenticator.__init__` gains `attempts: AttemptLedger`.
- `register(email, password, source: AttemptSource) -> UserId` and `sign_in(email, password, source: AttemptSource) -> IssuedSignIn`.
- The bodies are unchanged from S-01 and ignore `attempts` and `source`.

#### 2. Source dependency and wiring

**File**: `backend/src/adapters/auth/router.py`, `backend/src/adapters/auth/compose.py`

**Intent**: The router hands a source to the authenticator, and production wires the Postgres ledger.

**Contract**:
- `async attempt_source(request: Request) -> AttemptSource` is a FastAPI dependency. In this phase it returns the peer host, or `"unknown"` when `request.client` is `None`.
- `register` and `sign_in` routes pass it through.
- `compose.py` builds `SqlAlchemyAttemptLedger(_session_factory, DEFAULT_ATTEMPT_LIMITS)` into `_authenticator`.

#### 3. Test call sites

**File**: every `Authenticator(` construction and `register(`/`sign_in(` call in `backend/tests/`, found by grep. Today that includes `tests/unit/auth/test_authenticator.py` and `tests/integration/test_auth_http.py`.

**Intent**: Keep existing suites compiling and green.

**Contract**: Construct with `InMemoryAttemptLedger(DEFAULT_ATTEMPT_LIMITS)`, and call with a module-private `_sample_source()`.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd backend && uv run basedpyright`.
- The existing backend suite still passes: `cd backend && uv run pytest -m "not postgres"`.

---

## Phase 4: Limits in the authenticator — behavior

### Overview

Registration and sign-in consult, record, and clear the ledger (AC-18, AC-19).

### Changes Required:

#### 1. Authenticator tests

**File**: `backend/tests/unit/auth/test_authenticator.py`

**Intent**: Pin the ordering and counting rules through the public surface, with a real `InMemoryAttemptLedger` using small limits.

**Contract**: Tests:
- sign-in is refused with `TooManyAttemptsError` once failures reach the limit, even with correct credentials;
- a successful sign-in clears earlier failures, so the source again has the full allowance;
- registration beyond the limit is refused and persists no account;
- a refused registration counts, whether the email is already registered or the password is too short.

#### 2. Authenticator behavior

**File**: `backend/src/adapters/auth/authenticator.py`

**Intent**: Refuse before any store read or hashing, and count exactly what the requirements count.

**Contract**:
- `sign_in`: `attempts.ensure_allowed(SIGN_IN, source)`, then lookup and verify. On `InvalidCredentialsError`, call `attempts.record(SIGN_IN, source)` and re-raise. On success, call `attempts.clear(SIGN_IN, source)`.
- `register`: `attempts.ensure_allowed(REGISTRATION, source)`, then `attempts.record(REGISTRATION, source)`, then the S-01 flow.

### Success Criteria:

#### Automated Verification:

- Authenticator tests pass: `cd backend && uv run pytest tests/unit/auth/test_authenticator.py -v`.
- The full backend suite passes: `cd backend && uv run pytest -m "not postgres"`.
- Type check passes: `cd backend && uv run basedpyright`.

---

## Phase 5: Source resolution and HTTP refusal — stubs

### Overview

Materialize the operator settings, the source resolver, and the trusted-proxy provider, while keeping the peer-host behavior.

### Changes Required:

#### 1. Settings

**File**: `backend/src/config/settings.py`

**Intent**: Let the operator tune limits and declare trusted proxies.

**Contract**: New fields:
- `auth_sign_in_max_failures: int = 5`
- `auth_sign_in_failure_window_minutes: float = 15.0`
- `auth_registration_max_attempts: int = 10`
- `auth_registration_window_minutes: float = 60.0`
- `auth_trusted_proxy_addresses: list[str] = []`

#### 2. Source resolver

**File**: `backend/src/adapters/auth/source.py`

**Intent**: A pure function deciding who a request comes from, testable without HTTP.

**Contract**: `resolve_attempt_source(peer: str | None, forwarded_for: str | None, trusted_proxies: frozenset[str]) -> AttemptSource`. The stub body returns `peer` or `"unknown"`.

#### 3. Wiring

**File**: `backend/src/adapters/auth/compose.py`, `backend/src/adapters/auth/router.py`

**Intent**: Settings drive limits and trust, and tests can override trust.

**Contract**:
- `get_trusted_proxy_addresses() -> frozenset[str]` comes from settings.
- `_authenticator`'s ledger gets `AttemptLimits` built from the settings fields. A non-positive value fails at import with `NonPositiveAttemptLimitError`.
- `attempt_source` depends on `get_trusted_proxy_addresses` and delegates to `resolve_attempt_source(request.client.host, request.headers.get("x-forwarded-for"), trusted)`.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd backend && uv run basedpyright`.
- The existing backend suite still passes: `cd backend && uv run pytest -m "not postgres"`.

---

## Phase 6: Source resolution and HTTP refusal — behavior

### Overview

The source honors trusted proxies only, and a limited attempt answers 429 with `Retry-After` (AC-18, AC-19, AC-20).

### Changes Required:

#### 1. Source resolver tests

**File**: `backend/tests/unit/auth/test_source.py`

**Intent**: Pin that forwarded headers are trusted only from declared proxies.

**Contract**: Tests:
- the peer is the source when the peer is not trusted, even when `X-Forwarded-For` is present;
- the rightmost untrusted `X-Forwarded-For` entry is the source when the peer is a trusted proxy.

#### 2. HTTP tests

**File**: `backend/tests/integration/test_auth_http.py`

**Intent**: Pin the wire contract a client sees.

**Contract**: The stack uses small limits and overrides `get_trusted_proxy_addresses` with `frozenset({"testclient"})`. Tests:
- once failures reach the limit, sign-in answers 429 `too_many_attempts` with a positive integer `Retry-After`;
- registration beyond the limit answers 429 `too_many_attempts`;
- a sign-in with a different `X-Forwarded-For` is not refused while another source is limited.

#### 3. Resolver behavior

**File**: `backend/src/adapters/auth/source.py`

**Intent**: Walk `X-Forwarded-For` from the right, past trusted proxies, only when the peer is trusted.

**Contract**:
- Entries are comma-split and stripped. The first entry from the right that is not in `trusted_proxies` wins.
- When every entry is trusted, or the header is absent, the source is the peer.

#### 4. Retry-After header

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Tell clients how long to wait without importing the exception class.

**Contract**: When `getattr(exc, "retry_after_seconds", None)` is an `int`, the `JSONResponse` carries `Retry-After: <seconds>`. The body stays `{code, detail}`.

### Success Criteria:

#### Automated Verification:

- Source and auth HTTP tests pass: `cd backend && uv run pytest tests/unit/auth/test_source.py tests/integration/test_auth_http.py -v`.
- The full backend suite passes: `cd backend && uv run pytest`.
- Type check passes: `cd backend && uv run basedpyright`.
- Lint passes: `cd backend && uv run ruff check`.

#### Manual Verification:

- With the backend running, send six `curl -i -X POST localhost:8000/auth/sign-in -H 'content-type: application/json' -d '{"email":"a@example.com","password":"wrong-password"}'` requests. The sixth answers `429` with a `Retry-After` header.
- With `AUTH_REGISTRATION_MAX_ATTEMPTS=2` set, the third `POST /auth/register` within an hour answers `429`.

---

## Phase 7: TUI refusal — stubs

### Overview

Widen the API outcomes with the new refusal, so Phase 8's tests can import them.

### Changes Required:

#### 1. Outcome types

**File**: `tui/src/api/auth.ts`

**Intent**: Represent a rate-limited refusal as an outcome, not a thrown error.

**Contract**: `RegisterOutcome` and `SignInOutcome` each gain `{ kind: "too_many_attempts"; retryAfterSeconds: number | null }`. The mapping bodies are unchanged.

#### 2. Command switch

**File**: `tui/src/auth/command.ts`

**Intent**: Keep the exhaustive switches compiling.

**Contract**: `runRegisterCommand` and `runSignInCommand` each gain a `too_many_attempts` case that calls `deps.err("Too many attempts.")` and returns 1.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`.
- Lint passes: `cd tui && pnpm lint`.
- The existing TUI suite still passes: `cd tui && pnpm test`.

---

## Phase 8: TUI refusal — behavior

### Overview

The TUI maps 429 to the outcome and tells the person how long to wait.

### Changes Required:

#### 1. API and command tests

**File**: `tui/test/auth.test.ts`, `tui/test/authCommand.test.ts`

**Intent**: Pin the mapping and the message.

**Contract**: Tests:
- `signIn` returns `too_many_attempts` with `retryAfterSeconds` read from `Retry-After` on a 429 `too_many_attempts`;
- `register` does the same;
- `weles sign-in` prints `Too many attempts. Try again in about N minutes.`, with minutes rounded up and at least 1, exits 1, and writes no credential;
- `weles register` prints the same message and exits 1.

#### 2. Mapping and message

**File**: `tui/src/api/auth.ts`, `tui/src/auth/command.ts`

**Intent**: Read the refusal and phrase the wait.

**Contract**:
- A 429 with code `too_many_attempts` maps to the outcome. `retryAfterSeconds` is the parsed `Retry-After` header, or `null` when it is missing or not a positive integer.
- The command prints `Too many attempts. Try again in about ${Math.max(1, Math.ceil(s / 60))} minutes.`, or `Too many attempts. Try again later.` when the value is `null`.

### Success Criteria:

#### Automated Verification:

- Auth API and command tests pass: `cd tui && pnpm vitest run test/auth.test.ts test/authCommand.test.ts`.
- The full TUI suite passes: `cd tui && pnpm test`.
- Type check passes: `cd tui && pnpm typecheck`.
- Lint passes: `cd tui && pnpm lint`.

#### Manual Verification:

- With the backend running, run `weles sign-in <email>` five times with a wrong password, then once more. The sixth run prints `Too many attempts. Try again in about 15 minutes.` and exits 1.

---

## Testing Strategy

### Unit Tests:

- `AttemptLedger` contract over in-memory and Postgres (Phase 2).
- `Authenticator` ordering and counting (Phase 4).
- `resolve_attempt_source` trust rule (Phase 6).
- TUI API mapping and command messages (Phase 8).

### Integration Tests:

- `/auth/sign-in` and `/auth/register` answer 429 with `Retry-After`, and sources stay independent (Phase 6).

### Manual Testing Steps:

- The curl recipes in Phase 6 and the TUI recipe in Phase 8.

## Performance Considerations

- A sign-in or registration adds one or two small Postgres round trips. That is acceptable, because FR-009 exempts sign-in and registration from its no-database rule.
- A refused attempt does no Argon2 work, which lowers per-attempt CPU cost under guessing.
- `record` prunes a key's expired rows, so `auth_attempts` holds at most `max_attempts` live rows per active key, plus stale keys that are never touched again.

## Migration Notes

- One new table, `auth_attempts`, with no data backfill. Downgrade drops it.
- The migration chains onto the current single head.
- Without `AUTH_TRUSTED_PROXY_ADDRESSES`, an instance behind a reverse proxy counts every client as one source. The deployment effort must set it for the hosted instance.

## References

- `context/efforts/auth-flow/roadmap.md` — slice S-07
- `context/efforts/auth-flow/prd.md` — FR-010, Open Question 2
- `context/efforts/auth-flow/stories.md` — US-07, AC-18, AC-19, AC-20
- `context/archive/changes/2026-09-14-auth-flow-sign-in-gate/plan.md` — the auth adapter this change extends
- `context/efforts/deployment/research.md:36-40` — TLS terminated at the Mikrus edge, proxy headers
- `context/foundation/rules/exceptions.md` — mapping ownership and exhaustiveness
