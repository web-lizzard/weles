---
change_id: capture-command-graph-walk
title: Capture's reply command walks its graph instead of routing phases itself
status: new
created: 2026-09-12
updated: 2026-09-12
archived_at: null
origin: llm-adapter-distill-live
---

## Notes

Capture's GenerateReplyCommand stops routing phases itself (`_dispatch` in application/capture/commands/send_message.py picks DRAFTING via available_transitions) and walks the graph through the shared StateMachine.advance() introduced by llm-adapter-distill-live, so the command no longer knows capture's route. Carry-over caveats from that discover-contracts session: (1) not behaviour-neutral — today a turn never returns from drafting to conversing, while looping advance until refusal would take DRAFTING→CONVERSING when conversation_requested holds; the per-turn move budget must be decided explicitly; (2) capture streams to HTTP, so the walk must interleave `advance` with each phase's stream inside the command (llm-adapter-distill-live dropped its GraphDispatcher; distill's command loops over `advance` directly); (3) depends on advance landing in llm-adapter-distill-live first.
