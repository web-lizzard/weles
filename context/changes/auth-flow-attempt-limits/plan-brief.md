# Attempt Limits — Plan Brief

> Full plan: `plan.md`

## What & Why

Anyone who learns an instance's address can guess passwords and register accounts as fast as the instance answers, and every attempt costs an Argon2 hash. This change limits repeated sign-in and registration attempts from one source (FR-010, AC-18, AC-19, AC-20) and resolves PRD Open Question 2.

## Starting Point

S-01's `adapters/auth/` registers accounts and signs people in with no attempt counting. The TUI throws on any status it does not map.

## Desired End State

- **Sign-in.** After 5 failed sign-ins in 15 minutes, a source gets 429 `too_many_attempts` with `Retry-After`, even with correct credentials and before any hashing. A success clears the failures.
- **Registration.** After 10 registrations in an hour, a source is refused the same way.
- **Other sources.** They are never affected.
- **TUI.** It prints how many minutes to wait.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Limits | 5 failed sign-ins in 15 min, 10 registrations in 60 min, operator-tunable | OWASP-aligned, tolerant of typos, and cuts guessing to about 480 attempts a day | Plan |
| Source | Peer address; `X-Forwarded-For` only from `AUTH_TRUSTED_PROXY_ADDRESSES` | Works behind the Mikrus edge (AC-20) and cannot be spoofed without a proxy | Plan |
| Counter storage | `AttemptLedger` port, in-memory and Postgres adapters, one contract | The roadmap requires both adapters, and counters survive restarts | Roadmap / Plan |
| What counts | Sign-in failures only, cleared on success; every registration attempt | Matches AC-18 and AC-19 without penalizing a person who got in | Plan |
| Check order | Ledger before account lookup and Argon2 | A refused attempt costs almost nothing | Plan |
| Refusal | 429 `too_many_attempts` plus `Retry-After`, added by `errors.py` from an attribute | Standard signal, and the rule against importing exception classes in the HTTP adapter holds | Plan |
| TUI message | `Too many attempts. Try again in about N minutes.` | The person knows how long to wait | Plan |
| Window | Sliding, pruned on `record` | No burst at window edges, and the table stays bounded | Plan |

## Scope

**In scope:**
- Ledger port and both adapters.
- `auth_attempts` migration.
- `Authenticator` limiting.
- Source resolver.
- Settings.
- 429 with `Retry-After`.
- TUI outcome and message.

**Out of scope:**
- BDD scenarios, which come from the `/bdd` lane.
- Configuring the hosted instance's proxy, which belongs to `deployment`.
- Per-account lockout.
- CAPTCHA.
- DDoS protection.
- Limits on gated routes.
- Atomic check-and-record.

## Architecture / Approach

```
POST /auth/sign-in ─► attempt_source(request) ─► resolve_attempt_source(peer, XFF, trusted)
                   └► Authenticator.sign_in(email, pw, source)
                         ├─► AttemptLedger.ensure_allowed ──► TooManyAttemptsError ─► 429 + Retry-After
                         ├─► AccountStore.by_email ─► PasswordHasher.verify
                         └─► fail: ledger.record · success: ledger.clear
AttemptLedger = InMemoryAttemptLedger | SqlAlchemyAttemptLedger (auth_attempts)
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Ledger — stubs | Port, value objects, exceptions, map entries, adapter shells | Exhaustiveness test goes red without map entries |
| 2. Ledger — behavior | Contract over both adapters, `auth_attempts` migration | Migration branching off the wrong head |
| 3. Authenticator — stubs | `attempts` and `source` threaded through every call site | Missed test call sites |
| 4. Authenticator — behavior | Check before hashing, record failures, clear on success | Recording on the wrong branch |
| 5. Source & HTTP — stubs | Settings, resolver signature, trusted-proxy provider | Non-positive settings at import |
| 6. Source & HTTP — behavior | Trusted-proxy rule, 429 plus `Retry-After` | Trusting `X-Forwarded-For` from an untrusted peer |
| 7. TUI — stubs | Widened outcomes, switch cases | — |
| 8. TUI — behavior | 429 mapping, wait message | Missing or garbage `Retry-After` |

**Prerequisites:**
- `TEST_DATABASE_URL` for the postgres lane.
- A running backend with `AUTH_SIGNING_SECRET` for the manual checks.

**Estimated effort:** 8 small phases, about 2 sessions of `/unit-test` → `/implement` cycles.

## Open Risks & Assumptions

- A concurrent burst can overshoot a limit by its parallelism, because check and record are not atomic. That is accepted for a nice-to-have.
- Behind the Mikrus edge, all clients share one counter until `AUTH_TRUSTED_PROXY_ADDRESSES` is set by the deployment effort.
- An attacker rotating many source addresses is not stopped. Per-account lockout is out of scope.

## Success Criteria (Summary)

- Backend (both lanes), basedpyright, ruff, TUI test, typecheck, and lint are green.
- A sixth wrong sign-in from curl answers 429 with `Retry-After`, while a different source still signs in.
- `weles sign-in` tells the person how many minutes to wait.
