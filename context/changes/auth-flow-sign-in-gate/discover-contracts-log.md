## Current State

Session closed 2026-09-13. Every thread raised is settled or deliberately parked, and nothing is OPEN.

What the contract says, for a reader who reads nothing else. It is written as signatures, value objects, guards, and orchestration docstrings, with no method bodies and no tests.

**Core.** `backend/src/domain/shared/identity/model.py` `UserId` is the only person-shaped thing in the core. No handler receives it in S-01, and S-04/S-05 thread it in as an explicit argument.

**Auth adapter (`backend/src/adapters/auth/`)**, the whole mechanism, with no domain or application layer:

- `model.py`:
  - `EmailAddress.parse` is the only entry. It uses EmailStr syntax and case-folds the whole address.
  - `PasswordPolicy` has a guarded floor of 8.
  - `SigningSecret` has no default and is guarded to at least 32 bytes.
  - `SignInLifetime` is guarded to be greater than 0.
  - Also `Password` (`SecretStr`), `PasswordHash`, `Account`, and `IssuedSignIn`.
- `ports.py`: async Protocols.
  - `AccountStore` (`save`, `by_email`): `save` is the only uniqueness enforcement.
  - `SignInIssuer`: `Authenticator` only.
  - `SignInVerifier`: the gate only. It uses no DB, store, LLM, or network (FR-009).
- `tokens.py`: `SignInTokens` is the single local async implementation of both token ports, so there is no second signing adapter. Key material and lifetime are constructor input.
- `passwords.py`: `PasswordHasher`, concrete and async.
- `authenticator.py`:
  - `register`: policy -> hash -> `Account.register` -> `save`. It issues no sign-in.
  - `sign_in`: `by_email` -> verify -> issue.
- `in_memory_account_store.py`, `sqlalchemy_account_store.py` (own session and commit per `save`, unique violation -> `EmailAlreadyRegisteredError`), `sqlalchemy_models.py` (`auth_accounts`, unique `email`, registered in `backend/src/adapters/out/sqlalchemy/metadata.py`).
- `dto.py`, `router.py`, `compose.py`:
  - Public endpoints: `POST /auth/register` (201) and `POST /auth/sign-in`.
  - `require_sign_in` uses `HTTPBearer(auto_error=False)` and returns `UserId`.
- `exceptions.py`: `CoreException` subclasses, with codes in `backend/src/adapters/http/errors.py`.

**Uniform refusals.**
- `invalid_credentials` covers an unknown email, a wrong password, and an unparseable email at sign-in.
- `sign_in_required` covers a missing, malformed, altered, made-up, foreign-instance, or expired token.
- There is no timing equalisation, because registration already discloses whether an address exists.

**Gate.** `backend/src/main.py` denies by default. `health`, `auth`, and non-prod `outbox` mount on `app`, and `capture`, `notes`, and `remember` mount under `gated`, which depends on `require_sign_in`.

**TUI (`tui/src/`, declared signatures).**
- `api/auth.ts`: `register` and `signIn` return discriminated outcomes. `signIn` drops the token, so the TUI cannot keep or send it before S-03.
- `auth/command.ts`: `runRegisterCommand` and `runSignInCommand`. The email comes from argv. The password comes from the no-echo interactive prompt only, and a run without a TTY exits 1. Exit codes are 0/1/2.

Left for `/plan` and `/implement`:

- the `Settings` auth fields (`auth_signing_secret`, `auth_sign_in_lifetime_hours = 24`, `auth_password_min_length = 8`), kept out of this commit because of the user's uncommitted `settings.py` edit
- the Alembic revision for `auth_accounts`
- the concrete token and hashing libraries
- all method bodies
- BDD `dependency_overrides` for `require_sign_in` in the existing capture, distill, and remember suites. They pass today only because the gate has no body.
- `pnpm generate:api` for the auth paths
- `cli.tsx` dispatch of `register` and `sign-in`, and the `readSecret` implementation
- contract suites for `AccountStore` (in-memory + Postgres) and for the token ports (`SignInTokens`)

## Log

### 2026-09-13 — user-id-unbound: `UserId` enters the core as identity, not bound to handlers this session — ACCEPTED

The user: "do domeny dochodzi UserID jako tożsamość, nie musimy w tej sesji tego bindować".

**Why:** It matches the frame's `principal-threading` (S-01 only validates) and `identity-reader-port` (explicit argument, no reader). **Consequence:** `domain/shared/identity/model.py` holds `UserId` only. It sits in a subpackage, following `domain/shared/{outbox,graph,instruction}/`.

### 2026-09-13 — auth-in-adapter: the entire auth mechanism lives in the adapter layer — ACCEPTED

The user: "Cały mechanizm auth idzie do adaptera".

**Why:** Restates the frame's by-design out-of-scope line. **Consequence:** accounts, hashing, tokens, and orchestration all live under `backend/src/adapters/auth/`. Nothing in `domain/` or `application/` imports them.

### 2026-09-13 — auth-adapter-layout: core under `adapters/auth/`, storage under `adapters/out/{in_memory,sqlalchemy}/auth/`, router in `adapters/http/auth.py` — OPEN

**Why:** Storage implementations follow the existing technology split (`backend/src/adapters/out/sqlalchemy/metadata.py` imports per-context `models`, and BDD compositions import from `adapters/out/in_memory/<ctx>/`). The router follows `backend/src/adapters/http/*.py`. The alternative is one self-contained `adapters/auth/` package holding everything. Only `AccountStore` is a Protocol. Hasher and tokens have no I/O, so the InMemoryFirst rule is met by the real class.

### 2026-09-13 — auth-errors-root: auth errors are `CoreException` subclasses mapped in the one HTTP table — OPEN

**Why:** `context/foundation/rules/exceptions.md` keeps a single `code -> status` table in `backend/src/adapters/http/errors.py`, and an exhaustiveness test walks every `CoreException` subclass (`backend/tests/unit/test_http_error_mapping.py`). An adapter-local `HTTPException` would bypass both. The cost is that the rule currently names domain and application exceptions only.

### 2026-09-13 — gate-shape: deny by default through one gated parent router — OPEN

**Why:** The frame refuses every data or operation request (AC-11, AC-12). Adding a `Depends` to each router means a forgotten router is open, and middleware cannot be overridden by the BDD `dependency_overrides` pattern (`backend/tests/bdd/conftest.py`). Proposal: `main.py` mounts the public routes (`/health`, `/auth/*`, non-prod `/_outbox`) directly and every other router under an `APIRouter(dependencies=[Depends(require_sign_in)])`. `require_sign_in` uses `HTTPBearer`, returns `UserId`, and raises `SignInRequiredError`.

### 2026-09-13 — dirty-compose-settings: the session must edit files with the user's uncommitted changes — OPEN

**Why:** `backend/src/config/settings.py` (model names) and `backend/src/adapters/compose.py` (deterministic LLM override) carry uncommitted edits. The closing commit stages every touched file whole, and `git add -p` is interactive and forbidden. Wiring needs `Settings` fields (`auth_signing_secret`, `auth_sign_in_lifetime_hours = 24`, `auth_password_min_length = 8`) and compose getters.

### 2026-09-13 — uniform-refusals: one code per failure family, no reason leaked — OPEN

**Why:** `invalid_credentials` covers an unknown email and a wrong password (AC-04), and `sign_in_required` covers a missing, forged, or expired token (frame: made-up == no sign-in). No timing equalisation for unknown emails, since duplicate registration already discloses whether an address is registered (frame, `duplicate-registration-response`).

### 2026-09-13 — sign-in-token-ports: token signing and verification are async ports, split into issuer and verifier — ACCEPTED

The user: "interfejsy do podpisania i weryfikacji tokeny - chciałbym uzyć czegoś async pod spodem".

**Why:** An async implementation cannot sit behind the concrete synchronous `SignInTokens` drafted earlier. As Protocols, the choice of implementation stays outside the auth adapter's orchestration. The split is proposed in this entry, not asked for by the user: the gate gets only `SignInVerifier` and cannot issue, and `Authenticator` gets only `SignInIssuer`. One class may implement both. **Consequence:** the concrete `SignInTokens` class and `adapters/auth/tokens.py` are removed. Under InMemoryFirst and `context/foundation/rules/contract-testing.md`, both ports need an in-memory implementation (no I/O, e.g. stdlib HMAC over `SigningSecret` + `SignInLifetime`) and one contract suite that the async implementation also runs. Expiry must be contract-testable without frozen time (`context/foundation/testing-conventions.md`, Determinism), which is why the lifetime is constructor input. **Supersedes:** the concrete `SignInTokens` shape recorded in the 2026-09-13 Current State (it had no log entry of its own).

### 2026-09-13 — sign-in-token-backend: what "async underneath" runs on — OPEN

**Why:** It decides whether the FR-009 invariant needs tightening. A local async library keeps verification in-process. A remote signer or key service (KMS, Vault) would put a network call on every gated request, which is outside the letter of FR-009 ("database or LLM") but not its intent, which is that an unidentified caller costs the instance nothing. For a remote backend, the verifier contract would probably have to say "no network I/O per request", for example through cached public-key verification.

### 2026-09-13 — sign-in-token-backend: one local async implementation, no second signing adapter — ACCEPTED

The user: "nie będę robił dwóch adapterów na podpis".

**Why:** A single implementation that the contract suite runs on every CI invocation cannot be remote, so it is local and async. That keeps InMemoryFirst satisfied without a separate in-memory double, and it settles the FR-009 question: `SignInVerifier` now also forbids network I/O. **Consequence:** `adapters/auth/tokens.py` `SignInTokens` implements both `SignInIssuer` and `SignInVerifier`. **Supersedes:** the 2026-09-13 `sign-in-token-backend` OPEN entry, and the in-memory-plus-async consequence of the 2026-09-13 `sign-in-token-ports` ACCEPTED entry.

### 2026-09-13 — auth-adapter-layout: everything under `adapters/auth/` — ACCEPTED

The user: "Adapters/auth wszystko".

**Why:** The auth adapter is self-contained and has no hexagonal layers. Keeping router, composition, stores, and ORM row together makes that boundary a directory. **Consequence:** `router.py`, `compose.py`, `in_memory_account_store.py`, `sqlalchemy_account_store.py`, and `sqlalchemy_models.py` live in `adapters/auth/`. The only reach outside is `backend/src/adapters/out/sqlalchemy/metadata.py` importing the row for Alembic, and `backend/src/adapters/compose.py` is no longer touched. **Supersedes:** the 2026-09-13 `auth-adapter-layout` OPEN entry.

### 2026-09-13 — auth-errors-root: auth errors are `CoreException` subclasses — ACCEPTED

The user: "wyjątki auth jako CoreException".

**Why:** One `code -> status` table and the existing exhaustiveness test (`backend/tests/unit/test_http_error_mapping.py`) cover them. **Supersedes:** the 2026-09-13 `auth-errors-root` OPEN entry.

### 2026-09-13 — gate-shape: gated parent router, two public auth endpoints — ACCEPTED

The user: "może być bramka przez nadrzędny router, tylko dwa endpointy do auth".

**Why:** Deny by default means a router added later is gated unless someone mounts it on `app` on purpose. **Consequence:** the public surface is `/health`, `POST /auth/register`, `POST /auth/sign-in`, and non-prod `/_outbox` (frame, Boundaries). Everything else sits under `gated` in `backend/src/main.py`. **Supersedes:** the 2026-09-13 `gate-shape` OPEN entry.

### 2026-09-13 — dirty-compose-settings: only `settings.py` still collides — OPEN

The user asked whether the session had added anything to those files. It had not: both diffs predate the session (git status at session start). The session has edited only `backend/src/adapters/http/errors.py` among pre-existing files, plus `main.py` and `metadata.py`, which were clean.

**Why:** With auth composition in `adapters/auth/compose.py`, `compose.py` is out of the way. `Settings` has `extra="forbid"` over `.env` (`backend/src/config/settings.py`), so a separate auth settings class cannot share the file, and the three fields must go into `Settings`.

### 2026-09-13 — account-store-commit: SQLAlchemy account store commits per `save` — OPEN

**Why:** `context/foundation/rules/cqrs-lite.md` puts the commit boundary in an application `UnitOfWork`, but auth has no application layer (frame) and registration is one row. The alternative is an auth-local unit of work, which is machinery for a single insert.

### 2026-09-13 — account-store-commit: SQLAlchemy account store commits per `save` — ACCEPTED

The user: "pasuje".

**Why:** Auth has no application layer or `UnitOfWork` (frame), and registration writes one row. **Supersedes:** the 2026-09-13 `account-store-commit` OPEN entry.

### 2026-09-13 — dirty-compose-settings: `Settings` auth fields left to plan and implement — PARKED

The user: "na razie zostaw, zrobi to plan implement po plan".

**Why:** The fields are mechanical and the user's uncommitted `settings.py` edit stays out of this session's commit. **Revisit when:** `/plan auth-flow-sign-in-gate` writes the wiring phase. **Supersedes:** the 2026-09-13 `dirty-compose-settings` OPEN entry.

### 2026-09-13 — tui-password-entry: email as argument, password through a no-echo prompt only — OPEN

**Why:** The frame gives register and sign-in TUI commands of their own. `tui/src/cli.tsx` dispatches subcommands through `meow`, and `runInstanceCommand` takes `(args, deps)` (`tui/src/instance/command.ts`). A password in argv lands in shell history. The open question is whether a non-TTY stdin pipe is also accepted, for scripting.

### 2026-09-13 — tui-sign-in-drops-token: `signIn` does not return the token — OPEN

**Why:** The frame says the TUI neither keeps nor sends a sign-in until S-03. Dropping the token at the API module makes that structural rather than a convention S-03 could silently break early. S-03 widens `SignInOutcome` on purpose.

### 2026-09-13 — tui-password-entry: interactive no-echo prompt only — ACCEPTED

The user: "tylko prompt".

**Why:** A password in argv lands in shell history, and piped stdin is not needed by any story. **Consequence:** `tui/src/auth/command.ts` invariants refuse argv and piped input and exit 1 without a TTY. **Supersedes:** the 2026-09-13 `tui-password-entry` OPEN entry.

### 2026-09-13 — tui-sign-in-drops-token: `signIn` does not return the token — ACCEPTED

The user: "zgoda".

**Why:** The TUI neither keeps nor sends a sign-in until S-03, and dropping the token at `tui/src/api/auth.ts` makes that structural. **Supersedes:** the 2026-09-13 `tui-sign-in-drops-token` OPEN entry.

### 2026-09-13 — uniform-refusals: one code per failure family, no reason leaked — ACCEPTED

The user: "pasuje".

**Why:** AC-04 and the frame's "made-up token == no sign-in". An unparseable email at sign-in also yields `invalid_credentials`. There is no timing equalisation, since duplicate registration already discloses existence. **Supersedes:** the 2026-09-13 `uniform-refusals` OPEN entry.
