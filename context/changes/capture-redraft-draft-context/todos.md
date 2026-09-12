---
change_id: capture-redraft-draft-context
current_phase: 2
next_step: 2.4
next_command: /implement capture-redraft-draft-context phase 2
updated: 2026-09-13
---

### Phase 1: Stubs — declare the hydration action

#### Automated

- [x] 1.1 Declare `_hydrate_draft_from_note` (unimplemented) and wire it into `Drafting.get_actions` for `UserMessageRecorded` — 0b9a441

### Phase 2: Behavior — rebuild the draft from the persisted note

#### Tests

- [x] tests generated — 5111852

#### Automated

- [x] 2.1 Implement `_hydrate_draft_from_note` via `deps.note_vocabulary.resolve`
- [x] 2.2 Add `test_capture_graph.py` cases: hydrates from persisted note; no-ops with an existing draft; no-ops with no note
- [x] 2.3 Add `test_send_message_command.py` regression: redraft that skips re-proposing topic no longer raises `DraftTopicMissingError`

#### Manual

- [ ] 2.4 Run the full backend suite
