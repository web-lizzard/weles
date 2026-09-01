# Property test review — capture-flow-draft-note phase 3

ran at ee230e7

| Field | Value |
| --- | --- |
| change-id | capture-flow-draft-note |
| scope | phase 3 |
| engine | Hypothesis 6.165.10 (pytest host) |
| date | 2026-09-01 |
| max_examples | 100–500 per property |
| vector | input-space / boundary |

## Oracle-able surface

- `backend/src/domain/capture/value_objects.py` — `Label`, `Embedding`, `NoteContent` validators
- `backend/src/domain/capture/topic.py` — `Topic.mint`
- `backend/src/domain/capture/tag.py` — `Tag.mint`
- `backend/src/domain/capture/note.py` — `Note.draft`
- `backend/src/domain/capture/capture_session.py` — `CaptureSession.draft_note`

## Properties hunted

1. **Label canonicalization** — a constructed `Label` stores `strip(raw)`, not the raw input.
2. **NoteContent canonicalization** — same rule for `NoteContent`.
3. **Length after strip** — padded strings whose stripped core is within `LABEL_MAX_LENGTH` / `NOTE_CONTENT_MAX_LENGTH` are accepted and store the stripped value.
4. **Acceptance oracle** — accept iff `0 < len(strip(s)) <= MAX`; reject otherwise (differential against strip-then-measure model).
5. **Whitespace-only rejection** — strings drawn from ASCII/nbsp whitespace alphabets that strip to empty always raise `EmptyLabelError` / `EmptyNoteContentError`.
6. **Tag order preservation** — `Note.draft` `tag_ids` equals `[tag.id for tag in tags]` for arbitrary tag list lengths.
7. **Session linkage** — `CaptureSession.draft_note` sets `session.note_id` to the returned note's id.
8. **UTC timestamps** — `Topic.mint` and `Tag.mint` stamp `created_at` with `UTC` tzinfo.

## Specimens

**no new edge found**

## Classified (not triaged)

- **Zero-width / format characters as label content** — inputs such as `\u200b` (zero-width space) are accepted because `str.strip()` does not remove them and the plan's "empty" invariant is defined post-`strip()`. Treating these as empty would require a stronger normalization oracle than the documented trim-then-validate contract; classified as property too strong, not a specimen.

## Retractions

(none)
