# Card-to-Anchor Jump — Plan Brief

> Full plan: `plan.md`

## What & Why

From a card, the user reaches its note with the source fragment marked in place (AC-13 / FR-013). Anchor resolution moves out of the adapter parser and into the distill domain, so one rule serves both the generation-time grounding check and the read-time jump. The backend resolves the position; the TUI renders it without knowing anything about markdown.

## Starting Point

Cards carry a verbatim `anchor.quote` and grounding runs through the `NoteDocumentParser` port, whose markdown adapter answers a boolean and discards positions. The read surface exposes no position at all, and the TUI renders a note as one undifferentiated block of text with no jump gesture.

## Desired End State

`GET /notes/{note_id}` additionally returns ordered `blocks`; `GET /notes/{note_id}/cards` returns each live card's `anchor_location` — block index, bounds within that block, and a precision of `exact` or `block` — or `null` when the quote no longer resolves. In the TUI, `Enter` on a card's detail opens the note tab rendered from the anchored block downward with the passage marked; an unresolved anchor opens the note from the top under a visible notice.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where the mechanism lives | `NoteDocument` value object in the domain; the parser port is deleted | One rule in one place means the grounding check and the jump cannot drift apart. | Plan |
| Markdown syntax knowledge | A `NoteFormat` strategy protocol in the same domain package, with `MarkdownNoteFormat` as its only implementation | Keeps the matching rule free of syntax so a rich-text format is a new class, not a rewrite. | Plan |
| Wire shape | `blocks` on note detail, `anchor_location` on each card | Resolution happens once, server-side; the client stays a rendering layer. | Plan |
| Highlight granularity | Exact span, degrading to the whole block | Precise where the offset map recovers cleanly, never worse than block-level. | Plan |
| Unresolvable anchor | `null` location, note opens with a visible notice | Reading is never blocked and the degradation is loud, as the ADR argued. | Plan |
| Jump gesture | `Enter` on card detail | The key is free on that screen and already means "act on this" everywhere else. | Plan |
| Fragment visibility | Render from the anchored block downward; no general scrolling | Guarantees the fragment is visible without pulling S-04's deferred scroll model into this slice. | Plan |
| AC-13 coverage | US-07 feature file plus TUI tests | The logic now lives in the backend, so acceptance coverage belongs there too. | Plan |

## Scope

**In scope:** the `NoteFormat` strategy and `NoteDocument`/`AnchorLocation` value objects; retiring the `NoteDocumentParser` port, adapter, contract suite and injection; `blocks` and `anchor_location` on the two read DTOs; the US-07 acceptance feature; the TUI jump gesture, highlight rendering and anchored viewport.

**Out of scope:** general note scrolling; persisted anchor positions; a jump from the card list row; any non-markdown `NoteFormat`; note editing, card regeneration or removal; FR-014; quotes spanning two blocks.

## Architecture / Approach

`NoteFormat` answers two questions about a serialization format — how content splits into blocks, and how a block normalizes into comparable text plus an offset map back to the raw characters. `NoteDocument` holds the blocks and that format, and `locate(anchor)` carries the rule: normalize the quote, take the first block containing it, map the match back through the offsets, and report `exact` or degrade to `block`. `GenerateCards` derives `AnchorResolution` from whether `locate` returned anything, so the port and its composition wiring disappear; the two query adapters build the same document to fill the read model. Nothing new enters `compose.py` — a strategy with a default is not a port.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Domain anchor-location contracts | `NoteFormat`, `NormalizedText`, `NoteBlock`, `AnchorLocation`, `NoteDocument` as stubs | Wrong offset semantics baked into the contract |
| 2. Domain anchor-location behavior | Markdown strategy with its offset map, plus the matching rule and both precisions | The character-by-character offset map is the hardest code in the change |
| 3. Generation on the domain locator | Port, adapter, contract suite and injection removed; six test surfaces migrated | A missed call site leaves generation ungrounded without a red test |
| 4. Read-model anchor contracts | `blocks` and `anchor_location` DTO fields wired to empty values | A required field breaking an existing adapter construction |
| 5. Read-model behavior and US-07 acceptance | Both query adapters resolving; HTTP coverage; the AC-13 feature | Precision serialization drifting from the domain enum |
| 6. TUI anchor surface stubs | Regenerated schema, client types, highlight state | Regeneration needs a running backend |
| 7. Jump gesture and anchored highlight | `Enter` jump, marked fragment, anchored viewport, unresolved notice | Note rendering moves from one string to blocks — spacing regressions |

**Prerequisites:** S-04 (note detail) and S-06 (cards tab), both archived. Phases 4 and 6 need a locally running backend.

**Estimated effort:** seven phases; the backend is five of them and carries the difficulty.

## Open Risks & Assumptions

- The offset map is a rewrite, not a wrapper: today's `re.sub`/`replace` normalization cannot be adapted, so phase 2 is where this change can slip.
- Deleting the parser port touches six test surfaces at once; phase 3 has no new tests, so it relies entirely on the existing suites staying green.
- `NoteDetailDTO` carries both `content` and `blocks`. Deliberate redundancy — blocks are derived on every read, so they cannot diverge.
- This reverses ADR `distill-domain-shape` alternative 12, which placed the matching rule in an adapter. Recorded on the change's `adr_refs`; the ADR text still says otherwise.
- The anchored viewport renders from the highlighted block downward, so content above the fragment is unreachable until the user leaves and re-enters the tab.

## Success Criteria (Summary)

- A card's `Enter` opens its note with the quoted passage marked and visible without scrolling.
- A card whose quote no longer resolves opens the note readable, under a notice rather than silently unmarked.
- `uv run pytest`, `uv run pytest tests/bdd -m "distill-flow and AC-13"`, and the TUI's `pnpm test` all pass, with no reference to `NoteDocumentParser` left in the tree.
