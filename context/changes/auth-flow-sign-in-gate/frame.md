---
status: closed
created: 2026-09-14
updated: 2026-09-14
---

## Boundaries

In scope:

- A person registering on an instance and signing in to it, without anyone else acting.
- Refusing every request for data, or for a capture, distill, or remember operation, that carries no valid sign-in. The refusal is identical on an instance running on localhost.
- What that refusal costs the instance. PRD FR-009 has no story and is carried by this slice (`context/efforts/auth-flow/roadmap.md`, S-01).
- A credential that the instance did not issue, whether made up, altered, or malformed, counts as no valid sign-in. It is refused on the same terms as a request that carries no credential at all, and without consuming database or LLM resources.
- A sign-in is accepted only by the instance that issued it. Each instance has its own means of issuing sign-ins, and nothing shipped in the public repository, image, or TUI lets anyone produce a sign-in that an instance accepts.
- A sign-in stops being accepted once its validity period has passed. The period is set per instance and defaults to one day. S-03 still owns expiry during in-progress work (AC-07, AC-08) and settles the final period (PRD Open Question 1).
- A sign-in that is still within its validity period cannot be withdrawn by the instance before it expires. This consequence of refusing forged credentials without a lookup is accepted.
- Identity as the core sees it. A person reaches the core domain only as a user identifier shared by every bounded context, which is the key that S-04 and S-05 attach data to. Nothing else about a person enters the core. Wherever an application handler learns who is acting, it receives that identifier as an explicit input from the input adapter. The core holds no ambient "current user" reader.
- Registration refuses an email address that is not syntactically valid. Two addresses that differ only in letter case, anywhere in the address, or in surrounding whitespace name the same person.
- Registering an email address that already names a registered person is refused, the response says that the address is already registered, and it grants no access to that person's data.
- Registration refuses a password shorter than the instance's configured minimum. The operator may raise the minimum but can never set it below 8 characters.
- Registering and signing in behave the same against an in-memory account store, which is what the acceptance tests run on, as against Postgres, which has its own Alembic revision.
- `/health` and the non-production outbox inspection route stay reachable without sign-in. Neither returns captures, notes, cards, or review history: the outbox route lists envelope metadata only (`backend/src/application/shared/outbox/dto.py`), and it is not mounted in production (`backend/src/main.py:40-41`).
- Registering and signing in from the TUI, as commands of their own. A successful sign-in confirms that the instance accepted the credentials. The TUI neither keeps the sign-in nor sends it with later requests.

Out of scope:

- Separating data between signed-in people. Until `auth-flow-capture-distill-separation` (S-04) and `auth-flow-remember-separation` (S-05) land, every signed-in person on an instance still sees the same captures, notes, cards, and review history. This is acceptable only because the hosted instance stays off public addresses until PRD FR-007 and FR-008 hold (`context/efforts/auth-flow/roadmap.md`, S-04).
- Handing the user identifier to capture, distill, and remember handlers. In this slice the gate only admits or refuses a request. Handlers start receiving the identifier in S-04 and S-05.
- The TUI keeping a sign-in, sending it with its requests, refusing to be used without one, and never sending one instance's sign-in to another instance after an address switch. These belong to S-03 (`auth-flow-sign-in-lifetime`), which persists the sign-in (AC-06). The instance-binding handover from S-02 (`context/archive/changes/2026-09-13-auth-flow-instance-address/plan.md:66-67`) moves there for its TUI half. The backend half, a sign-in accepted only by its issuing instance, stays here. Until S-03 lands, the instance refuses the TUI's capture, notes, and remember requests. This is accepted because S-03 follows this change directly and no instance is deployed.
- Signing out (S-06).
- Limiting repeated sign-in or registration attempts (S-07). Until S-07, each attempt's hashing cost goes unlimited. This is accepted because no instance is deployed before this effort completes.
- Password reset, account recovery, password change, account deletion, data export, signing in with an external account, proving control of an email address, a registration gate or allowlist, and revoking access (`context/efforts/auth-flow/prd.md`, Non-Goals).

Out of scope, by design:

- Modelling accounts, credentials, registration, or sign-in as a bounded context with its own domain and application layers. Authentication is a supporting concern with no business rules of Weles's own. It lives in an auth adapter, which is wired into HTTP and mints the shared user identifier.

## Requirements

- **AC-03** — `context/efforts/auth-flow/stories.md`, US-02.
- **AC-04** — `context/efforts/auth-flow/stories.md`, US-02.
- **AC-05** — `context/efforts/auth-flow/stories.md`, US-02.
- **AC-11** — `context/efforts/auth-flow/stories.md`, US-05.
- **AC-12** — `context/efforts/auth-flow/stories.md`, US-05.
- **AC-13** — `context/efforts/auth-flow/stories.md`, US-05.
- **PRD FR-009** — carried without a story (`context/efforts/auth-flow/stories.md`, Uncovered Requirements).
