---
change_id: capture-redraft-draft-context
title: Restore in-memory draft context on redraft passes through the capture machine
status: new
created: 2026-09-13
updated: 2026-09-13
archived_at: null
origin: llm-adapter-instruction-context
effort_id: llm-adapter
---

## Notes

### Wniosek (z debugowania `draft_topic_missing`)

Po `draft_done` sesja zostaje w fazie `DRAFTING` (redraft bez ponownej zgody — zgodnie z istniejącymi testami). Każdy nowy `POST /messages` buduje świeży `CaptureTurn`: `session.phase` i `note_id` są w DB, ale **`turn.draft` nie jest persystowane** — startuje jako `None`.

Kolejny request w `DRAFTING` to więc redraft z pustym draftem w pamięci, podczas gdy topic/tagi już żyją na zapisanej notatce. Model i adapter zakładają kolejność topic → tagi → treść; bez odtworzenia draftu pierwsze `NoteContentProduced` / `propose_note_content` kończy się `DraftTopicMissingError`.

**UoW sam nie wystarczy** — transakcja nie przechowuje `turn.draft`. Repozytoria z UoW są tylko źródłem danych do odtworzenia.

**Właściwe miejsce:** graf / `CaptureMachine` (np. `prepare_drafting_turn()`, akcja na `UserMessageRecorded` w stanie `Drafting`, lub równoważny hook obok `_resolve_note_topic`), nie ad-hoc w `GenerateReplyCommand`. Tymczasowa hydratacja w komendzie została wycofana na rzecz tej zmiany.

**Poza zakresem tej zmiany (już na branchu):** guardy w `PydanticAiCaptureAgentAdapter` (stream/tool bez topicu → `ReplyProduced` / pominięcie tagu) — łagodzą kolejność od LLM, ale nie zastępują odtworzenia draftu na redrafcie.

### Planowane

- Zdefiniować invariant redraftu w domenie i podpiąć go pod maszynę.
- Test jednostkowy: drugi request w `DRAFTING` z istniejącą notatką nie rzuca `DraftTopicMissingError` gdy model woła treść przed ponownym `propose_note_topic` (lub bez niego, jeśli topic się nie zmienia).
