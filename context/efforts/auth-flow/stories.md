---
status: draft
version: 1
created: 2026-09-13
effort_id: auth-flow
---

# Auth flow

## Stories

### US-01 — Use the instance I choose

I want to point the TUI at an instance of my choosing so that the same public TUI works with my hosted instance or a private one without touching its code.

Realizes: FR-001

- AC-01: A person can make the published TUI work against an instance at an address they choose without changing its code or rebuilding it.
- AC-02: After the TUI is pointed at a different instance, none of its actions reach the previously chosen instance.

### US-02 — Get in without waiting for the owner

As the reviewer, I want to register and sign in on my own so that I can start using an instance whose address I was given without the owner having to do anything at that moment.

Realizes: FR-002, FR-003

- AC-03: A person with no account on an instance can register and then sign in without any other person acting.
- AC-04: A sign-in attempt with credentials that match no registered person does not grant access.
- AC-05: Registering under an identity already registered on that instance does not grant access to the existing person's data.

### US-03 — Stay signed in, but not forever

I want my sign-in to survive restarting the TUI yet run out after a few days so that I am not asked to sign in at every launch, and a sign-in left behind somewhere does not keep working indefinitely.

Realizes: FR-004, FR-005

- AC-06: Restarting the TUI while the sign-in is still valid does not require signing in again.
- AC-07: Once a sign-in outlives its validity period, it no longer grants access and the person must sign in again.
- AC-08: When a sign-in expires during a capture conversation or review sitting, the person is told that it expired and can sign in again, rather than losing the in-progress work without notice.

### US-04 — Sign out cleanly

I want to sign out so that I can switch to a different account on the same instance, for example to check what another person sees.

Realizes: FR-006

- AC-09: After signing out, the TUI cannot read or write any data on the instance until someone signs in again.
- AC-10: Signing in as a different person after signing out shows none of the previous person's data.

### US-05 — Strangers get nothing

I want a caller who is not signed in to be refused everything so that knowing my instance's address is not enough to read or change my notes.

Realizes: FR-007

- AC-11: A caller who is not signed in cannot read any captures, notes, cards, or review history on the instance.
- AC-12: A caller who is not signed in cannot create, change, or delete any data, or start any capture, distill, or review operation.
- AC-13: An instance running on localhost refuses a caller who is not signed in exactly as a hosted instance does.

### US-06 — My data is mine alone

I want everything I capture, distill, and review to be visible only to me so that another person on the same instance, such as the reviewer, neither sees my learning nor mixes into my review schedule.

Realizes: FR-008

- AC-14: A signed-in person cannot see any capture, note, card, or review history belonging to another person on the same instance.
- AC-15: Cards generated in the background from a person's notes appear only in that person's space.
- AC-16: A person's review sittings present only that person's own cards, and their review results change only their own schedule.
- AC-17: A signed-in person cannot change or delete another person's data.

### US-07 — Guessing my way in gets slow

I want repeated sign-in and registration attempts from a single source to be limited so that someone who learns my instance's address cannot cheaply guess their way into my account or flood the instance with registrations.

Realizes: FR-010

- AC-18: After repeated failed sign-in attempts from a single source, further sign-in attempts from that source are refused for a time.
- AC-19: Registration attempts from a single source beyond a limit are refused for a time.
- AC-20: A person signing in from a different source is not refused because of another source's attempts.

## Uncovered Requirements

- **FR-009** — The pass condition concerns what a rejection consumes inside the instance, which no user can observe; the user-facing payoff is carried by US-05, and the constraint goes to the roadmap and plan unstoried.
