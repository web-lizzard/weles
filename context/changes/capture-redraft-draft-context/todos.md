---
change_id: capture-redraft-draft-context
current_phase: 1
next_step: 1.1
next_command: /implement capture-redraft-draft-context phase 1
updated: 2026-09-12
---

### Phase 1: Stubs — declare the hydration action

#### Automated

- [ ] 1.1 Declare `_hydrate_draft_from_note` (unimplemented) and wire it into `Drafting.get_actions` for `UserMessageRecorded`

### Phase 2: Behavior — rebuild the draft from the persisted note

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Implement `_hydrate_draft_from_note` via `deps.note_vocabulary.resolve`
- [ ] 2.2 Add `test_capture_graph.py` cases: hydrates from persisted note; no-ops with an existing draft; no-ops with no note
- [ ] 2.3 Add `test_send_message_command.py` regression: redraft that skips re-proposing topic no longer raises `DraftTopicMissingError`

#### Manual

- [ ] 2.4 Run the full backend suite
