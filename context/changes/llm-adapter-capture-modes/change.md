---
change_id: llm-adapter-capture-modes
title: A capture session moves between conversing and note drafting on the user's word
status: preparing
created: 2026-09-12
updated: 2026-09-12
archived_at: null
effort_id: llm-adapter
slice_ref: S-02
---

## Notes

<!-- Materialized from effort `llm-adapter`, slice S-02. Run /plan llm-adapter-capture-modes to write the plan. -->

- `tests/unit/capture/contracts/test_message_repository_contract.py` is **skipped** until
  `InMemoryMessageRepository` implements `MessageRepository.history` (port extended during
  discover-contracts). Remove `pytestmark` when that adapter work lands in `/implement`.
