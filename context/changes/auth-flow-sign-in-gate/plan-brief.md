# Sign-In Gate — Plan Brief

> Full plan: `plan.md`

## What & Why

A person can register and sign in on a Weles instance, and every data or operation request without a valid sign-in is refused, on localhost too. Refusal costs no database or LLM work (FR-009). This is the identity foundation every later auth-flow slice stands on.

## Starting Point

The contract session (commit `66afdae`) left the full auth adapter, `UserId`, the deny-by-default gated router, and the TUI command signatures on disk, all with empty bodies. There are no token or hashing libraries, no auth settings, and no migration.

## Desired End State

`POST /auth/register` and `POST /auth/sign-in` work against Postgres. Capture, notes, and remember answer 401 `sign_in_required` to any caller without a genuine, unexpired sign-in from this instance. `weles register` and `weles sign-in` confirm credentials from the terminal and discard the token.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where auth lives | Self-contained `adapters/auth/`, only `UserId` in core | Auth is a supporting concern with no Weles business rules | Frame / Contracts |
| Credential shape | Self-verifying signed token, no lookup, no early invalidation | FR-009 forbids per-request DB work | Frame |
| Token library | PyJWT HS256 behind `async` port methods, `algorithms` pinned | No trustworthy async-native library exists, and HMAC is microseconds with no I/O | Plan |
| Password hashing | argon2-cffi (Argon2id) via `asyncio.to_thread` | Current first choice, and it is kept off the event loop | Plan |
| Signing secret | Required `AUTH_SIGNING_SECRET`, fail fast, dev value in gitignored `.env` | Nothing shipped may mint sign-ins; one rule on localhost too | Frame / Plan |
| Lifetime / password floor | 24h default; min length 8, operator may raise | Per-instance config with a hard floor | Frame |
| Refusals | `invalid_credentials` and `sign_in_required`, one code each | No reason is leaked | Contracts |
| Gate shape | Parent `gated` router in `main.py` | A forgotten router is closed, not open | Contracts |
| Existing suites | Override `require_sign_in` in fixtures | They test their feature, not the gate | Contracts |
| `settings.py` pending edit | Committed with Phase 5; red settings test aligned | User's choice | Plan |

## Scope

**In scope:**
- Registration and sign-in.
- The gate on capture, notes, and remember.
- The `auth_accounts` migration.
- In-memory and Postgres account stores.
- Token and account-store contract suites.
- TUI register and sign-in commands.

**Out of scope:**
- Handing `UserId` to handlers, and data separation (S-04, S-05).
- The TUI keeping or sending a token (S-03).
- Sign-out (S-06).
- Attempt limits (S-07).
- Revocation, reset, and other PRD Non-Goals.
- BDD scenarios, which come from the `/bdd` lane.

## Architecture / Approach

```
HTTP ─► adapters/auth/router ─► Authenticator ─► AccountStore (in-memory | Postgres)
   │                                  ├─► PasswordHasher (argon2, to_thread)
   │                                  └─► SignInTokens (issuer)
   └─► gated router ─► require_sign_in ─► SignInTokens (verifier, no I/O) ─► UserId
```

The phases go inside-out, and each one fills bodies behind failing tests written first. No stubs phases are needed, because the contracts already exist.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Value objects + hasher | Email identity, password floor, Argon2id | Case-fold subtleties beyond `EmailStr` |
| 2. Sign-in tokens | PyJWT issue and verify, token contract suite | Missed claim or alg pinning accepts forged tokens |
| 3. Account stores + migration | In-memory and Postgres stores, `auth_accounts` revision | Unique-violation mapping across drivers |
| 4. Authenticator | Register and sign-in orchestration | Hashing before the policy check |
| 5. HTTP + gate + wiring | Endpoints, active gate, settings, suite overrides | Existing suites going red all at once |
| 6. TUI API module | `register` and `signIn` outcomes, regenerated schema | Needs a running backend to regenerate |
| 7. TUI commands | `weles register` and `weles sign-in`, no-echo prompt | Raw-mode prompt behaviour across terminals |

**Prerequisites:** `TEST_DATABASE_URL` for the postgres lane (devcontainer provides it). A generated `AUTH_SIGNING_SECRET` in `backend/.env` before the Phase 5 manual checks.
**Estimated effort:** 7 phases, roughly 2–3 sessions of `/unit-test` → `/implement`.

## Open Risks & Assumptions

- Until S-03, the TUI's capture, notes, and remember calls are refused. This is accepted because nothing is deployed.
- Argon2 cost per attempt is unlimited until S-07. This is accepted for the same reason.
- `test_settings_defaults_distill_model_when_unset` is red before this change and is fixed inside Phase 5.

## Success Criteria (Summary)

- Backend suite (both lanes), basedpyright, and the TUI test, typecheck, and lint checks are all green.
- A made-up, altered, foreign, or expired token is refused exactly like no token, without touching stores.
- A person registers and signs in from both curl and the TUI.
