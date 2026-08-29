---
status: draft
version: 1
created: 2026-08-29
effort_id: capture-flow
---

# Capture flow — User Stories

## Stories

### US-01 — Surface understanding gaps through conversation

I want to start a conversation about a topic and have the agent probe my understanding with follow-up questions targeted at the shaky parts, so that gaps in my understanding surface while I still have the chance to work through them.

Realizes: FR-001, FR-002, FR-003

- AC-01: The user can start a capture session by naming a topic.
- AC-02: Over the course of the conversation, the agent asks follow-up questions in response to what the user says, rather than only recording it.
- AC-03: The agent indicates, gently and non-authoritatively, which parts of the user's explanation seem solid and which seem shaky.
- AC-04: Follow-up questions concentrate on the parts of the explanation flagged as shaky.

### US-02 — Retain control over when the conversation ends

I want the agent to tell me when it thinks we've covered the topic while leaving the decision to end the conversation with me, so that I don't get cut off before I'm ready or dragged out past the point of diminishing returns.

Realizes: FR-004, FR-005

- AC-05: The agent can proactively signal that it thinks the topic has been sufficiently covered.
- AC-06: The conversation phase continues until the user explicitly confirms they're done, regardless of the agent's signal.

### US-03 — Walk away without a trace

I want to abandon a capture session at any point before I approve it, so that I can bail on a conversation that isn't working without leaving junk behind.

Realizes: FR-006

- AC-07: Abandoning a session before approval results in no note or outbox entry being created.

### US-04 — Get a written note without writing it themselves

I want the agent to draft the note's topic, body, and tags from what we discussed, so that I never have to write up the note myself, and the note is filed under a topic precise enough to be useful later.

Realizes: FR-007, FR-008

- AC-08: At the end of the conversation, the agent produces a draft note with a topic, body, and tags derived from the discussion.
- AC-09: The draft's topic can be more specific than the topic the user originally named, when the conversation supports it.

### US-05 — Keep the topic/tag space clean

I want the agent to reuse an existing topic or tag when one is close enough, and to only mint and show me a new one when nothing fits, so that my topic and tag space doesn't fill up with near-duplicates I have to clean up later.

Realizes: FR-009, FR-010

- AC-10: When an existing topic or tag closely matches what the conversation is about, the agent reuses it instead of proposing a new one.
- AC-11: A new tag is minted only when no existing tag is a close match, and the user is shown it when this happens.

### US-06 — Reshape the draft conversationally

I want to see the drafted note and ask for changes in conversation until it's right, so that the final note matches what I actually meant without me having to edit the text directly.

Realizes: FR-011, FR-012

- AC-12: The user is shown the drafted note's topic, body, and tags before anything is saved.
- AC-13: The user can describe a change they want and receive a redraft reflecting it, without editing note text directly.

### US-07 — Stay in control of what gets saved

I want nothing to reach my notes until I explicitly approve the draft, so that I stay in full control of what becomes a permanent record.

Realizes: FR-013, FR-014

- AC-14: No note or tags are written to the outbox before the user gives explicit approval.
- AC-15: Once the user approves, the note and tags are sent to the outbox and the session ends.

## Uncovered Requirements

None — every functional requirement is realized by a story.
