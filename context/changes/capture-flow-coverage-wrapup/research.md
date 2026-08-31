---
date: 2026-08-31T14:05:02+00:00
topic: "Domain-model requirements the ADR imposes on the coverage/wrap-up change (S-02)"
topic_slug: null
container_id: capture-flow-coverage-wrapup
tags: [research, capture-flow, domain-model, adr, coverage, wrap-up]
last_updated: 2026-08-31
---

# Research: Domain-model requirements the ADR imposes on the coverage/wrap-up change (S-02)

## Research Question

syntezuj wymagania modelu z adra dotyczace tej zmiany

## Summary

`capture-flow-coverage-wrapup` is roadmap slice S-02 (`Users control when the conversation ends, even when the agent thinks it's done`), realizing AC-05/AC-06 (FR-004/FR-005) — strictly upstream of drafting (S-04) and independent of `Note`/`draft_note()` mechanics.

The governing ADR, `capture-flow-domain-shape`, imposes **no new domain state** for this slice. Its model already settles two facts that bound what S-02 may add:

1. `CaptureSession.status` has exactly two values, `open`/`closed`, and `closed` means specifically "approved, note sent" — the only transition into it is `approve()` → `close()`, gated on note approval (S-06), not on ending the conversation phase. The session therefore stays `open` through drafting and review; "the conversation phase ends" per AC-06 is not an aggregate-level state transition.
2. `Message` is immutable, append-only, with `role` closed to `user`/`agent` and no domain-computed sequence number — assembling/reading the transcript is a query concern, not a write-path one. The ADR's own consequences note that guarantees like "no messages after close" are enforced by the command handler checking `status`, not by the aggregate shape — exactly the pattern already implemented for S-01's `GenerateReplyCommand`.

Consistent with the ADR's explicit YAGNI stance elsewhere (no `abandon()`/`discard()`, `Note.status.discarded` left unreachable rather than modeled), nothing in the decision suggests a new persisted flag for "coverage reached" or "user confirmed done." Both are read naturally as **application-layer** concerns:

- **AC-05** (proactive coverage signal) is a new *judgment* to compute from the transcript and surface to the user — not a domain fact. It sits alongside the S-01-built `ConfidenceAssessmentPort`, which already takes the **full transcript**, not just the latest message (see Code References) — so the case for a *separate* port from `ConfidenceAssessmentPort` cannot rest on input granularity; both would receive the same `Transcript`. The real distinction is output semantics: `ConfidenceAssessment` is a list of per-claim `solid`/`shaky` points feeding follow-up-question generation (AC-03/AC-04), while AC-05 needs a single aggregate "is this topic sufficiently covered" judgment consumed differently (surfaced as a wrap-up suggestion, not folded into reply generation). Whether that judgment is a new port/value object or an added field on the existing `ConfidenceAssessment` shape is not settled by the ADR — the ADR's stated scope is the domain aggregates, not application-layer ports — and is left as an open question below.
- **AC-06** (agent's signal alone never ends the conversation) is a negative guarantee: further `send_message` calls must keep succeeding regardless of the AC-05 signal. This is testable today by the same `status == OPEN` guard pattern already used in `GenerateReplyCommand._get_open_session`, requiring no new domain method.
- The **explicit "user confirms done"** action has no natural domain-level effect to produce yet, since S-04 (drafting) is out of scope for S-02 and `draft_note()` is guarded only on `status == open` — a status `draft_note()` already permits regardless of any conversation-end signal. What, if anything, this action should persist before S-04 exists is an open question, not something the ADR resolves.

## Findings

### CaptureSession status is binary and closes only via approval

- `context/adrs/capture-flow-domain-shape/decision.md:21` — `CaptureSession` fields: `id`, `topic: str`, `status` (`open` | `closed`), `created_at`.
- `context/adrs/capture-flow-domain-shape/decision.md:24` — `draft_note(...)` guarded on `status == open`; no other status value is modeled.
- `context/adrs/capture-flow-domain-shape/decision.md:25-26` — `approve(note)` calls `note.approve(self.id)` then `self.close()`; `close()` is one-way and invoked only internally by `approve`.
- `context/adrs/capture-flow-domain-shape/decision.md:44` — `status: closed` "means specifically 'approved, note sent', not a generic terminal state."
- `backend/src/domain/capture/value_objects.py` (`SessionStatus` enum: `OPEN`, `CLOSED`) and `backend/src/domain/capture/capture_session.py:16-22` (`start()` only sets `OPEN`) confirm the current implementation carries no third status.

### Message/transcript mechanics keep "coverage" a read-side computation

- `context/adrs/capture-flow-domain-shape/decision.md:30` — `Message` is immutable, append-only, `role` a closed `user`/`agent` set.
- `context/adrs/capture-flow-domain-shape/decision.md:32` — no domain-computed sequence number; "assembling the full transcript ... is a **query**, not a write-path concern."
- `context/adrs/capture-flow-domain-shape/decision.md:62` — Consequences: `CaptureSession` does not structurally guarantee "no messages after close" by aggregate shape; that depends on the command handler checking status inside the shared `UnitOfWork`.
- `backend/src/application/capture/commands/send_message.py:57-64` (`_get_open_session`) already implements exactly this handler-side guard, raising `CaptureSessionClosedError` when `session.status != SessionStatus.OPEN` — the pattern any S-02 "end conversation" guard should reuse.

### The existing confidence-assessment port already receives the full transcript

- `backend/src/application/capture/ports.py:12-13` — `ConfidenceAssessmentPort.assess(self, transcript: Transcript) -> ConfidenceAssessment` takes the whole `Transcript`, not the latest message alone.
- `backend/src/adapters/out/in_memory/capture/confidence_assessment.py` — the deterministic adapter internally only reads `user_entries[-1]`, but that is an adapter-level choice, not a port-level constraint.
- `backend/src/application/capture/value_objects.py` — `ConfidenceAssessment` is `points: list[ConfidencePoint]`, each a `kind` (`solid`/`shaky`) plus a `note` about one claim — a per-claim, list-shaped output, structurally different from a single aggregate "covered" judgment.
- `backend/src/application/capture/commands/send_message.py:66-67` — `assessment` is computed every turn from the freshly queried `transcript` and threaded straight into reply generation; a coverage judgment would plug into the same per-turn point if reusing this flow.

### YAGNI precedent against inventing new persisted state

- `context/adrs/capture-flow-domain-shape/decision.md:44` — "There is **no** `abandon()` and no `discard()`. Abandonment is a non-event at the domain layer."
- `context/adrs/capture-flow-domain-shape/decision.md:67` (Consequences) — `Note.status` carries a `discarded` value "nothing can set," accepted as "an explicit call against this session's own YAGNI recommendation."
- `context/adrs/capture-flow-domain-shape/decision.md:80` (Alternative 7) — keeping `abandon()`/`discard()` was rejected because "it protects against nothing functional... nothing in v1 ever reads the resulting status back."

These read together as the ADR's consistent bias against adding domain state that nothing yet consumes — directly bearing on whether S-02's "confirm done" action needs any persisted trace before S-04 exists.

## Code References

- `context/adrs/capture-flow-domain-shape/decision.md:21` — `CaptureSession` field/status shape.
- `context/adrs/capture-flow-domain-shape/decision.md:24-26` — `draft_note`/`approve`/`close` guards and transitions.
- `context/adrs/capture-flow-domain-shape/decision.md:30,32` — `Message` shape, append-only, transcript-as-query.
- `context/adrs/capture-flow-domain-shape/decision.md:44` — meaning of `closed`; absence of `abandon()`/`discard()`.
- `context/adrs/capture-flow-domain-shape/decision.md:62,67,80` — consequences and rejected alternatives evidencing the ADR's YAGNI bias.
- `context/efforts/capture-flow/roadmap.md` — S-02 outcome, AC-05/AC-06, dependency on S-01, S-04's dependency on S-02.
- `context/efforts/capture-flow/stories.md` — US-02, AC-05, AC-06.
- `context/efforts/capture-flow/prd.md` — FR-004, FR-005.
- `backend/src/domain/capture/capture_session.py:9-27` — current `CaptureSession` implementation (`start`, `assign_topic`), no status beyond `OPEN`/`CLOSED`.
- `backend/src/domain/capture/value_objects.py` — `SessionStatus`, `Topic` (raw session-level label, distinct from the ADR's vocabulary `Topic` aggregate used on `Note`).
- `backend/src/domain/capture/message.py` — `Message.record(...)` factory matching the ADR's shape exactly.
- `backend/src/application/capture/commands/send_message.py:29-64` — `GenerateReplyCommand`, including the `status == OPEN` guard (`_get_open_session`) and per-turn `ConfidenceAssessmentPort` call.
- `backend/src/application/capture/ports.py:12-13` — `ConfidenceAssessmentPort` signature (full `Transcript` in, not last message).
- `backend/src/application/capture/value_objects.py` — `ConfidenceAssessment`/`ConfidencePoint` shape.

## Open Questions

1. Should the AC-05 coverage judgment be a new port/value object (e.g., a `CoverageAssessmentPort` returning a `covered: bool`/score), or an extension of the existing `ConfidenceAssessment` shape reusing `ConfidenceAssessmentPort`? The ADR does not decide this — it governs domain aggregates, not application-layer ports — and `ConfidenceAssessmentPort` already receiving the full transcript removes the strongest argument for a separate port on input-access grounds alone.
2. What, if anything, should an explicit "user confirms done" action persist or do at the domain/application level, given `CaptureSession` has no status between `open` and `closed`, `draft_note()` is guarded only on `open`, and S-04 (drafting) is out of scope for this change? Candidates: (a) no backend command at all for S-02 — the frontend alone decides when to invoke S-04 later; (b) a no-op/acknowledgment endpoint as a forward-looking seam for S-04. Neither is settled by the ADR or the PRD.
