---
feature: "Auth flow"
effort_id: auth-flow
version: 1
status: draft
created: 2026-09-13
context_type: brownfield
---

## Problem & Outcome

The author wants to hand their hosted Weles instance to a certification reviewer, but today the backend checks no identity at all: anyone who knows the address can read and write everything, and the reviewer's captures, cards, and review history would mix into the author's own notes and review schedule. The same gap blocks running a private instance, for example one per repository inside a devcontainer: the public TUI has no supported way to point at "my" instance and identify the person using it.

When this lands, every person on any Weles instance registers and signs in on their own and works in a space whose data nobody else sees, across the whole capture → distill → remember chain. A caller who is not signed in gets no data, and rejecting them costs the instance neither database nor LLM resources.

## User & Persona

The author: the operator of an instance who is also its main user, working through technical material with Weles. They reach for this feature when they are about to share the address of their hosted instance with the certification reviewer, and when they start a private instance and point the TUI at it.

### Secondary persona

The certification reviewer, and anyone running their own instance. They receive or know an address, register, and use the full chain without the operator having to act.

## Success Criteria

### Primary
- A reviewer who knows only the address registers and completes capture → distill → remember without the author acting at that moment. Neither person sees any of the other's captures, notes, cards, or review history at any stage.
- Every request for data or for capture/distill/remember operations made without a valid sign-in is rejected, and the rejection consumes neither database nor LLM resources. This can be checked.

### Secondary
- Repeated sign-in and registration attempts from a single source are limited.

### Guardrails
- The author's existing capture, distill, and remember flows behave as before, apart from signing in.
- An expiring sign-in never silently discards an in-progress capture conversation or review sitting. The person is told and can sign in again.
- The same identity rules apply on every instance, including a local instance on localhost. No instance is trusted because of where it runs.
- The author's hosted instance is not reachable at a public address until FR-007 and FR-008 hold.

## Functional Requirements

### Instance & account

- FR-001: Person can point the TUI at an instance of their choosing through a supported TUI action, without editing code or rebuilding; pointing it at a different instance replaces the previous one. Priority: must-have
- FR-002: Person can register on an instance without anyone else having to act. Priority: must-have
- FR-003: Registered person can sign in to the instance. Priority: must-have
- FR-004: Signed-in person stays signed in across TUI restarts until they sign out or their sign-in expires. Priority: must-have
- FR-005: Sign-in expires after a bounded period of a few days, after which the person must sign in again. Priority: must-have
- FR-006: Signed-in person can sign out. Priority: must-have

### Access & separation

- FR-007: Person who is not signed in cannot read or write any data on the instance. Priority: must-have
- FR-008: Person's captures, notes, cards (including cards generated in the background from their notes), and review history are visible only to that person. Priority: must-have
- FR-009: Instance rejects a request for data or for capture/distill/remember operations that carries no valid sign-in, without consuming database or LLM resources. Sign-in and registration themselves are not covered. Priority: must-have
- FR-010: Instance limits repeated sign-in and registration attempts from a single source. Priority: nice-to-have

## Non-Functional Requirements

- The public repository, the published TUI, and the deployment and CI configuration committed to the public repository name no particular instance.
- The hosted instance's address is hard to discover, not merely unpublished: it cannot be derived by enumerating a shared-domain naming pattern and does not surface through public certificate logs. Choosing the address belongs to the `deployment` effort.

## Non-Goals

- Password reset or account recovery. Without email confirmation there is no safe recovery channel; a person who forgets their password registers again into an empty space.
- Password change. Not needed for a two-person, certificate-driven deployment.
- Account deletion and data export. Out of this ship's core purpose of gating and separating access.
- Signing in with an external account (for example GitHub). A private instance must work without registering anything with a third party, and the reviewer must not need an account elsewhere.
- A registration gate or operator-controlled allowlist. Deliberately deferred while the only intended users are the author and one reviewer; revisit triggers live in `frame-log.md` (`operator-configured-allowlist`).
- Revoking a person's access. Meaningless while a revoked person could simply register again; returns with the registration gate.
- Proving control of an email address at registration. Low stakes while data is separated per person; returns with the registration gate.
- In-app protection of LLM spend. Spend is capped at the LLM provider; once hit, LLM-backed steps stop for every user of the instance, the owner included, and that is accepted.
- Protection against volumetric flooding (DDoS). An identity check runs only after traffic reaches the service; this is an edge concern for the `deployment` effort.
- Registration spam consuming database resources. Accepted cost of ungated registration; FR-009 deliberately does not cover sign-in and registration, and FR-010 only softens it.
- A TUI holding several instances at once. One instance at a time for now.
- Migrating or reassigning existing data. No persistent database is connected yet, so every instance starts empty.
- Publishing images or packages and hosting instances. These belong to the `deployment` effort.
- Teams, shared workspaces, or any data visible to more than one person. Weles stays a single-person instrument; a second person gets a separate space.

## Open Questions

1. **How long exactly does a sign-in stay valid ("a few days")?** — Owner: implementation, resolved at `/plan`. Block: no.
2. **What attempt limit counts as enough for FR-010?** — Owner: implementation, resolved at `/plan`. Block: no.
