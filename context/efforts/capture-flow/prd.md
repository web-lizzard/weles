---
feature: "Capture flow"
effort_id: capture-flow
version: 1
status: draft
created: 2026-08-29
context_type: greenfield
---

## Problem & Outcome

The Weles user writes notes by hand, alone — nothing checks along the way whether they actually understand the topic they're writing about. Shallow or wrong understanding slips into the system unnoticed, and may only surface later (if ever) once a flashcard exposes the gap.

Capture flow puts a conversation in front of that gap: the user talks through a topic, the agent gently pushes on the parts that are shaky, and the session ends with a note and tags that reflect understanding actually worked through in the conversation — without the user having to write the note themselves — and nothing is kept unless the user explicitly says so.

## User & Persona

The single Weles user — someone working through technical material (books, courses, projects). They reach for capture right after or during learning something, wanting to turn what's fresh in their head into a lasting note without doing the write-up themselves.

## Success Criteria

### Primary
- A capture session that ends in approval produces a note and tags in the outbox that reflect a multi-turn Socratic exchange, not a single-shot dump, with a topic and tags the user explicitly signed off on.
- The user never hand-writes the note or its tags — the agent drafts both from the conversation.

### Secondary
- Close topics and tags from prior sessions are reused instead of spawning semantic near-duplicates.
- Capturing a note this way costs the user less effort than writing one by hand.

### Guardrails
- Nothing is written to the outbox without the user's explicit approval.
- The agent's assessment of correctness is delivered gently and non-authoritatively — it never overwrites the user's own explanation as a flat "wrong" without room for the user to push back.
- Abandoning a session before approval leaves no residual note or outbox entry.

## Functional Requirements

### Session start & conversation

- FR-001: User can start a capture session by naming an initial topic. Priority: must-have
- FR-002: Agent conducts an interactive, Socratic conversation about the topic, asking follow-up questions rather than passively logging what the user says. Priority: must-have
- FR-003: Agent gently signals which parts of the user's explanation are solid and which need work, then asks deepening follow-up questions targeted at the weak parts. Priority: must-have
- FR-004: Agent tracks a running sense of how well the topic has been covered and may proactively suggest that the conversation is ready to wrap up. Priority: must-have
- FR-005: Only the user's explicit confirmation ends the conversation phase and moves to drafting; the agent's suggestion alone never ends it. Priority: must-have
- FR-006: User can abandon a capture session at any point before approval, leaving no note or outbox entry behind. Priority: must-have

### Draft & approval

- FR-007: At the end of the conversation, agent drafts a note (topic, body, tags) synthesized from the discussion. Priority: must-have
- FR-008: The session's topic label crystallizes over the course of the conversation; the agent may propose a more specific topic than the user's initial input for semantic precision. Priority: must-have
- FR-009: Before proposing a new topic or tag, agent checks existing topics/tags for a close match and reuses it instead of minting a near-duplicate. Priority: must-have
- FR-010: A new tag is minted, and shown to the user, only when no existing tag fits. Priority: must-have
- FR-011: Agent presents the drafted note's shape (topic, body, tags) to the user for review. Priority: must-have
- FR-012: User can request changes to the draft conversationally, and the agent redrafts accordingly; there is no direct inline text editing in this flow. Priority: must-have
- FR-013: Nothing is sent to the outbox until the user gives explicit approval of the shown draft. Priority: must-have
- FR-014: On approval, the approved note and tags are sent to the outbox and the session is closed. Priority: must-have

## Non-Goals

- Session persistence, listing, and reopening/resuming a capture session. Deferred to a separate future effort with its own PRD — the storage, session-state model, and resume semantics are real scope beyond this ship's core loop.
- Direct inline/manual editing of the drafted note's text. Reshaping happens only through conversational feedback, keeping v1's interaction surface to one mode.
- Authoritative fact-checking against external sources. The agent's correctness signal is its own best-effort judgment, delivered non-authoritatively — a confidently wrong "correction" is worse than a gentle nudge, and verifying against a source of truth is out of scope for this ship.
- Splitting one capture session into multiple notes. A session always yields at most one note, matching the session-level topic/tag embedding design already settled in the `overview-thougts` duck session.
- Flashcard generation ("distill"). Operates on notes already saved, via a separate worker/flow.
- The "remember" review flow. A separate main-loop command, not part of capture.

## Open Questions

1. **How is the topic-coverage/confidence signal actually computed (what counts as "well covered")?** — Owner: implementation, resolved at `/plan`. Block: no.
2. **What counts as a "close match" when checking existing topics/tags for reuse — exact string, or a semantic similarity threshold?** — Owner: implementation, resolved at `/plan`. Block: no.
3. **Is there a limit on reshape rounds before the flow forces a decision, or is it open-ended?** — Owner: user. Block: no (default: open-ended until the user is satisfied).
