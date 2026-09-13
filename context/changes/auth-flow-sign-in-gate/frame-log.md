## Current State

Session closed 2026-09-14. Every thread raised is settled in `frame.md`. Nothing is open inside this frame.

Downstream, not this frame's to settle: S-03 (`auth-flow-sign-in-lifetime`) grows. It takes the token sent on TUI requests, the TUI guard without sign-in, and the TUI half of instance binding handed over from S-02, and it should follow this change directly. `/roadmap auth-flow` owns amending that slice's text.

## Log

### 2026-09-14 — identity-model: minimal person record (id, email, password hash) — OPEN

**Why:** The user's opening proposal. The effort research (`research-domain-tenancy-and-adapter-grain.md`) calls for a stable `UserId` principal entering at HTTP and later stamped on aggregates. It adds no further account fields, since every field-bearing feature (roles, email proof, revocation, allowlist) is parked in `context/efforts/auth-flow/prd.md` Non-Goals. The open gaps are not fields: credential shape, instance binding, email equivalence for AC-05.

### 2026-09-14 — context-shape: new auth context vs adapter plus shared identity VO — OPEN

**Why:** The user asks which. Grounding: `context/foundation/rules/layering.md` (nothing upstream imports a concrete adapter), the InMemoryFirst and single-`save` hard rules (`CLAUDE.md`), and research problem class 4, "composition-smuggled semantics" (`research-domain-tenancy-and-adapter-grain.md`, Named problem classes). A user store owned only by an adapter would make S-04/S-05 domain roots reference an identity minted outside the hexagon. The per-request check, however, must stay outside repositories (FR-009). Working position: shared `UserId`, a small account context, and the gate in the HTTP adapter.

### 2026-09-14 — credential-self-verifiable: FR-009 forbids a per-request credential lookup — OPEN

**Why:** Raised as a reframe of "session = row in DB". PRD FR-009: rejection "without consuming database or LLM resources". A caller sending a made-up token is exactly the unidentified caller. If validating it needs a Postgres read, the Neon compute-hour exhaustion from the effort frame (`context/efforts/auth-flow/frame-log.md`, `ddos-scope` ACCEPTED) is back. Cost: no server-side invalidation before expiry, accepted only if revocation stays parked (`context/efforts/auth-flow/frame.md`, FR-04).

### 2026-09-14 — instance-bound-sign-in: a sign-in is valid only on the instance that issued it — OPEN

**Why:** Ownership handed over by S-02 (`context/archive/changes/2026-09-13-auth-flow-instance-address/plan.md:66-67`). Every instance runs the same public artifact (`context/efforts/auth-flow/frame.md`, Boundaries). A secret or default baked into it would let anyone mint sign-ins for every instance, making FR-007 hollow for any caller who reads the repo.

### 2026-09-14 — weak-password-before-limits: S-01 ships before attempt limits exist — OPEN

**Why:** The user asked whether later slices cover rate limiting. They do: S-07 `auth-flow-attempt-limits` realizes FR-010 (AC-18..AC-20), with prerequisite S-01 only and marked nice-to-have (`context/efforts/auth-flow/roadmap.md`, S-07; `prd.md`, FR-010). That leaves a window, possibly permanent if S-07 is never done, in which sign-in has no guessing limit. Registration spam's DB cost is an accepted non-goal (`prd.md`, Non-Goals), but the CPU cost of hashing on every attempt is not mentioned anywhere. The exposure is bounded by the hosted instance staying off public addresses (`context/efforts/auth-flow/frame.md`, Boundaries).

### 2026-09-14 — credential-self-verifiable: a credential the instance did not issue is no sign-in — ACCEPTED

**Why:** The user: "zmyślony token == nieprawdziwy". Under PRD FR-009 such a request is refused without database or LLM work, the same as one carrying no credential. **Consequence:** in-scope boundary in `frame.md`. The follow-on cost is split out as `no-early-invalidation`. **Supersedes:** the 2026-09-14 `credential-self-verifiable` OPEN entry.

### 2026-09-14 — no-early-invalidation: a genuine sign-in cannot be cut short before expiry — OPEN

**Why:** This follows from `credential-self-verifiable`. Recognising a credential without a lookup means there is no stored record to delete. Explained to the user on request, and awaiting their view. It is consistent with revocation being parked (`context/efforts/auth-flow/frame.md`, FR-04). It shapes what S-06 sign-out can promise (AC-09 is about the TUI, not about a copied credential).

### 2026-09-14 — context-shape: shared `UserId` in the core, auth as an adapter without hexagonal layers — ACCEPTED

The user: auth has no business value and is a supporting domain, so it gets no domain or application layer. The core holds the user id, and everything else goes to an auth adapter wired into HTTP.

**Why:** A proportionate call. The account rules found so far (email equivalence, uniqueness, the same failure for an unknown email and a wrong password) are generic authentication rules, not Weles rules. The objection raised earlier, that the tenancy key would be "minted outside the hexagon", was weaker than stated. An adapter constructing a domain value object does not break `context/foundation/rules/layering.md`, because adapters depend on domain. What layering forbids is the core importing the adapter, and a shared `UserId` avoids that. **Consequence:** identity boundary and out-of-scope line in `frame.md`. The open follow-ups are `identity-reader-port` and `auth-adapter-test-double`. **Supersedes:** the 2026-09-14 `context-shape` OPEN entry.

### 2026-09-14 — identity-model: minimal account record kept, owned by the auth adapter — ACCEPTED

**Why:** id, email, and password hash (plus `created_at`) stand, and no parked feature needs more. With `context-shape` settled, the record is auth-adapter state and only the id crosses into the core. **Supersedes:** the 2026-09-14 `identity-model` OPEN entry.

### 2026-09-14 — identity-reader-port: what "a port to read the user id" means — OPEN

**Why:** The user proposes such a port as the core's protection layer, implemented by the auth adapter. An ambient reader collides with the process-wide singletons in `backend/src/adapters/compose.py:251-261` (research problem class 7) and with worker-driven commands that have no request (`backend/src/adapters/out/worker/handlers/flashcard_gen.py:21-40`). An explicit `UserId` argument needs no port. The intent has to be pinned before contracts.

### 2026-09-14 — auth-adapter-test-double: acceptance tests need the account store without Postgres — OPEN

**Why:** `context/efforts/auth-flow/roadmap.md` S-01 requires in-memory and SQLAlchemy adapters, and the BDD lane runs on in-memory compositions (`backend/tests/bdd/conftest.py`). An adapter-only auth still needs a Postgres-free variant for AC-03..05.

### 2026-09-14 — identity-reader-port: explicit `UserId` argument, no reader port — ACCEPTED

The user: "faktycznie mniej maszynerii jak userId będzie przekazywane do handlerów".

**Why:** An ambient reader would collide with the request-shared singletons in `backend/src/adapters/compose.py:251-261` and has no source in worker-driven commands (`backend/src/adapters/out/worker/handlers/flashcard_gen.py:21-40`). An explicit argument works for both. **Consequence:** the identity boundary in `frame.md` states handlers receive `UserId` as input. When S-01 starts threading it stays open as `principal-threading`. **Supersedes:** the 2026-09-14 `identity-reader-port` OPEN entry.

### 2026-09-14 — lifetime-split: S-01 sign-in lasts only for the TUI process — ACCEPTED

The user: "na razie nie przetrwa (to zrobimy s-03 bo w s-01 i tak będzie sporo)".

**Why:** S-01 is already large (auth adapter, gate, TUI sign-in, instance binding), and AC-06 belongs to S-03 (`context/efforts/auth-flow/roadmap.md`). **Consequence:** out-of-scope line in `frame.md`. Whether the S-01 token expires is split out as `s01-token-expiry`.

### 2026-09-14 — weak-password-before-limits: minimum of 8, operator-raisable, never lower — ACCEPTED

The user: "minimum hasła na 8 (konfigurowane w settingsach, ale i tak nie mniejsze niż 8)".

**Why:** Unlimited guessing is possible until S-07, which is nice-to-have, so the floor is the only S-01 defence against trivial passwords. **Consequence:** in-scope line in `frame.md`. Hashing CPU per attempt stays open as `hashing-cpu-before-limits`. **Supersedes:** the 2026-09-14 `weak-password-before-limits` OPEN entry.

### 2026-09-14 — gated-surface: health and non-prod outbox route stay open — ACCEPTED

The user: "Nie bramkujemy outbox".

**Why:** Correction to the earlier Current State: the outbox route does not expose envelope payloads. `OutboxEnvelopeDTO` carries id, type, status, attempts, timestamps, and the claimer only (`backend/src/application/shared/outbox/dto.py`), so it reveals no captures, notes, cards, or review history (AC-11). Residual exposure: `environment_name` defaults to `LOCAL` (`backend/src/config/settings.py:47`), so any instance not explicitly set to prod shows activity metadata (how many notes were approved, and when) to unsigned callers. Accepted as metadata, not data. **Consequence:** in-scope line in `frame.md`.

### 2026-09-14 — no-early-invalidation: accepted, invalidation machinery too costly — ACCEPTED

The user: "maszyneria unieważniania będzie droga, jak tak to zatwierdzam".

**Why:** Early invalidation needs a per-request lookup that breaks FR-009, or unreliable in-process state. With revocation parked (`context/efforts/auth-flow/frame.md`, FR-04) and a short validity period (`s01-token-expiry`), the exposure of a copied token is bounded. **Consequence:** in-scope line in `frame.md`. **Supersedes:** the 2026-09-14 `no-early-invalidation` OPEN entry.

### 2026-09-14 — s01-token-expiry: S-01 sign-ins expire, per-instance period, default one day — ACCEPTED

The user: "wygasa, też konfigurowalne, na dzień default".

**Why:** A non-expiring token combined with `no-early-invalidation` would be valid forever. **Consequence:** in-scope line in `frame.md`. S-03 keeps AC-07/AC-08 and PRD Open Question 1.

### 2026-09-14 — principal-threading: S-01 only validates; handlers get `UserId` in S-04 — ACCEPTED

The user: "s-04 w tym momencie przekazujemy do handlera, teraz tylko walidacja".

**Why:** It matches research direction "S-01: HTTP gate + principal type; no partial port filters" (`context/efforts/auth-flow/research-domain-tenancy-and-adapter-grain.md`, Direction for auth-flow slices) and avoids a dead parameter. **Consequence:** out-of-scope line in `frame.md`.

### 2026-09-14 — auth-adapter-test-double: account store has in-memory and Postgres variants — ACCEPTED

The user: "tak, najlepiej tak".

**Why:** The BDD lane runs on in-memory compositions (`backend/tests/bdd/conftest.py`), and roadmap S-01 requires both adapters. **Consequence:** in-scope line in `frame.md`. **Supersedes:** the 2026-09-14 `auth-adapter-test-double` OPEN entry.

### 2026-09-14 — instance-bound-sign-in: separate per instance — ACCEPTED

The user: "możemy zrobić osobny per instancja".

**Why:** A value shipped in the public artifact would let anyone mint sign-ins for every instance. **Consequence:** in-scope line in `frame.md`, including the TUI half handed over by S-02. **Supersedes:** the 2026-09-14 `instance-bound-sign-in` OPEN entry.

### 2026-09-14 — hashing-cpu-before-limits: no protection now — PARKED

The user: "nie dodajemy teraz, baza i tak jest na razie w kontenerze, deployment będzie dopiero po auth dostarczony, więc brak zagrożeń".

**Why:** No instance is reachable before this effort and `deployment` land (`context/efforts/auth-flow/frame.md`, Boundaries, sequencing). **Revisit when:** S-07 is planned, or a hosted instance is about to become reachable while S-07 is still pending. **Consequence:** folded into the S-07 out-of-scope line in `frame.md`.

### 2026-09-14 — email-equivalence: when two emails name the same person — OPEN

**Why:** AC-05 ("registering under an identity already registered does not grant access") is only testable once "the same identity" is defined. This was raised at session open but never put to the user.

### 2026-09-14 — tui-sign-in-entry: S-01 sign-in happens inside the running TUI, at every launch — OPEN

**Why:** Follows from `lifetime-split`. A token held only in-process cannot come from a separate CLI invocation (`tui/src/cli.tsx:13-24` has only the `instance` command, `tui/src/startup.ts:12-20` resolves only the address). A user-visible consequence that needs confirmation.

### 2026-09-14 — email-equivalence: Pydantic email validation, local-part case still open — OPEN

The user: Pydantic has a helper for validating emails, and that should be enough.

**Why:** Syntax validation is accepted and recorded in `frame.md`. `email-validator` is already locked (`backend/uv.lock:448`, pulled by `pydantic[email]` at `backend/uv.lock:518`), so there is nothing to add. Verified in-session with `uv run python`: `EmailStr` trims whitespace and lowercases the domain only (`'Adam@X.PL' -> 'Adam@x.pl'`, `'adam@x.pl' -> 'adam@x.pl'`). Validation therefore does not settle equivalence for AC-05. Local-part case folding is put back to the user.

### 2026-09-14 — tui-sign-in-entry: "a new TUI command" — which kind — OPEN

**Why:** The user chose a new TUI command. A CLI subcommand process exits, so its token is lost without on-disk persistence, which `lifetime-split` (ACCEPTED) keeps out of S-01. An in-TUI action or a register-only subcommand fits. Evidence: `tui/src/cli.tsx:13-24`, `tui/src/startup.ts:12-20`.

### 2026-09-14 — email-equivalence: whole address case-folded on top of EmailStr — ACCEPTED

The user: "rozszerzam EmailStr o normalizację".

**Why:** In-session check showed `EmailStr` leaves local-part case intact (`Adam@x.pl` != `adam@x.pl`), which would allow two accounts for one person under AC-05. **Consequence:** email line in `frame.md` updated. **Supersedes:** the 2026-09-14 `email-equivalence` OPEN entry.

### 2026-09-14 — tui-sign-in-entry: TUI register and sign-in commands, token not kept until S-03 — ACCEPTED

The user: prepare sign-in (adding an identity) now, verify it against the database, and S-03 wires it up, writing the token to disk and guarding TUI use without sign-in.

**Why:** It keeps S-01 small and matches `lifetime-split` (ACCEPTED): the command confirms the credentials and discards the token. **Consequence:** the in-scope TUI line and the S-03 out-of-scope line in `frame.md`. The TUI half of the S-02 instance-binding handover moves to S-03. The side effect is raised as `tui-broken-window`. **Supersedes:** the 2026-09-14 `tui-sign-in-entry` OPEN entry.

### 2026-09-14 — tui-broken-window: TUI unusable between S-01 and S-03 — OPEN

**Why:** The backend refuses unsigned requests from S-01 on (body, in scope), and the TUI sends nothing until S-03. This contradicts the bundling rationale in `context/efforts/auth-flow/roadmap.md` S-01. It is tolerable only because no instance is deployed and S-03 depends on S-01 alone. No bypass exists, since AC-13 requires the same rules on localhost.

### 2026-09-14 — tui-broken-window: TUI refused until S-03, accepted — ACCEPTED

The user: "może tak być nawet, że TUI bez tokena odrzuca — S-03 idzie zaraz za tą zmianą".

**Why:** The window is short and nothing is deployed. S-01's acceptance criteria stay observable at the backend. **Consequence:** the S-03 out-of-scope line in `frame.md` records the accepted window. The growth of S-03 is noted for `/roadmap`. **Supersedes:** the 2026-09-14 `tui-broken-window` OPEN entry.

### 2026-09-14 — duplicate-registration-response: say the address is already registered — ACCEPTED

The user: "tak".

**Why:** Enumeration of registered addresses is low-stakes while data is separated per person (S-04/S-05) and registration is ungated (`context/efforts/auth-flow/prd.md`, Non-Goals). An explicit answer lets a returning person know to sign in instead. **Consequence:** in-scope line in `frame.md`.
