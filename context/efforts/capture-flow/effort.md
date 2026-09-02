---
effort_id: capture-flow
title: Capture flow
status: active
created: 2026-08-29
updated: 2026-09-02
archived_at: null
origin: overview-thougts
adr_refs:
  - id: capture-flow-domain-shape
    kinds: [implements]
---

## Context

- Product framing: [`context/foundation/project-overview.md`](../../foundation/project-overview.md) — capture → distill → remember loop
- Technical shape (duck `overview-thougts`): [`context/duck-sessions/overview-thougts/log.md`](../../duck-sessions/overview-thougts/log.md) — capture path, outbox, approval policy

## Goal

Capture flow lets the single Weles user turn a live conversation about a topic into a persisted note: the agent runs an interactive, Socratic exchange that gently surfaces where the user's understanding is solid or shaky, drafts a note and tags from that exchange, and only sends it to the outbox once the user explicitly approves — so notes reflect genuinely worked-through understanding rather than a raw, unchecked dump, and every session ends in either an approved note or no trace at all.
