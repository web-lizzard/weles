# TUI Capture Screen Fixes — Plan Brief

> Full plan: `plan.md`

## What & Why

The capture screen overlaps its own input, prints markdown raw, and hides older conversation behind absolute full-screen overlays. This change rebuilds it in Claude Code's terminal style:
- history lives in native scrollback;
- a bounded live region holds a pinned draft, the tail, an activity indicator, a framed input, and a status line;
- notes and review sittings open as bottom panels.

## Starting Point

- `app.tsx` renders a fixed-height shell with absolute overlays.
- `CaptureScreen` stacks unbounded blocks and hides the brand with a row budget that counts transcript entries.
- There is no markdown rendering, and the store clears the draft on every submit.

## Desired End State

- Conversation scrolls into terminal history with the touchpad, and the input frame and status line never move.
- Replies, the draft, and the note body render as formatted markdown, including while streaming.
- The draft is pinned at the top and scrolls with ↑/↓.
- `/approve` wipes the screen and scrollback.
- `/notes` and `/remember` open bounded, keyboard-scrolled panels in place of the input.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| History mechanism | Ink `<Static>` into native scrollback | Touchpad scroll must reach history, as in Claude Code. | Frame |
| Overflow of a streaming reply | Commit only completed markdown blocks; show the tail of the in-progress block | Scrollback never holds half-formatted text. | Plan |
| Stable-block rule | Token followed by a blank line, lists held while continuable | Zero token changes over ~4,000 fuzzed documents. | Research |
| Draft across redraft turns | Previous draft stays until the next turn's first draft event | Keeps FR-08's pinned region from flickering. | Plan |
| Draft region cap | Half the terminal, ↑/↓ scroll | Draft and redraft reply stay visible together. | Plan |
| Markdown engine | `marked` lexer plus own chalk renderer, `wrap-ansi` `hard: true` | Gives exact row counts for the budget, with one light dependency. | Plan |
| Messages | Error and coverage banner transient in the live region; brand, topic, and receipt in history | Stale state doesn't pollute scrollback. | Plan |
| Panel height | Content height, capped at `rows - 1`, keyboard scroll inside | Short lists leave the conversation visible, like Claude Code dialogs. | Plan |
| Approve clear | `<Static key={historyEpoch}>` remount, then a clear sequence written through `useStdout().write` | Ink forgets old output, so it is never replayed. | Research |
| Live region height | Never more than `rows - 1` | At `rows` and above, Ink clears and replays the whole history. | Research |
| Resize | Accept old wrapping in scrollback | Matches Claude Code and needs no history re-render. | Plan |
| Obsolete layout tests | Rewritten in the phase that changes the behavior | The suite stays green after every phase. | Plan |

## Scope

**In scope:**
- capture screen and shell layout;
- markdown for replies, the draft, and the note body;
- activity indicator;
- pinned draft region;
- `/approve` hint;
- bottom panels for notes and sitting;
- approve clearing history.

**Out of scope:**
- backend and SSE;
- command semantics;
- mouse handling;
- interrupting a turn;
- indicators in panels;
- card markdown;
- re-wrapping history on resize.

## Architecture / Approach

The pipeline runs in four steps:
1. `renderConversationLines` combines the brand, receipt, and transcript with the streaming reply, rendered through `renderMarkdownLines` and `splitStableBlocks`, into exact screen lines.
2. `layoutCapture` (pure) turns rows, chrome, draft lines, and conversation lines into a committed count (monotonic, stable lines only), a draft window, a tail, and filler rows.
3. `ConversationHistory` emits committed lines to `<Static>`, and the live region renders `DraftRegion`, the tail, the messages, `ActivityIndicator`, `InputFrame`, and `StatusLine`, or a `BottomPanel` in place of the last three.
4. `historyEpoch` drives the clear sequence.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1–2. Markdown renderer | Formatted, hard-wrapped lines; stable/pending split | Renderer coverage of note constructs |
| 3–4. Capture layout | Pure line budget and draft window | Off-by-one pushing the frame to `rows` |
| 5–6. Chat store | Draft persistence, `historyEpoch`, `turnStartedAt`, topic entries | Draft replacement on the first event of a turn |
| 7–8. Activity indicator | Glyph, rotating verb, elapsed seconds | Fake-timer interplay with `useAnimation` |
| 9–10. Capture shell | Scrollback history, frame, status line, streaming markdown, approve clear | `<Static>` key and clear ordering replaying old output |
| 11–12. Draft region | Pinned, ↑/↓-scrolled draft with conversation flowing under it | Filler rows vs. terminal height at the bottom |
| 13–14. Bottom panels | Notes and sitting as bounded, scrolled panels with bottom hints | Five screens rewired; key conflicts with selection |

**Prerequisites:** none. The backend is needed only for Manual Verification.
**Estimated effort:** about 14 phases; the heaviest are 10, 12, and 14.

## Open Risks & Assumptions

- Terminals honour `ESC[3J`. Some (e.g. older tmux settings) keep scrollback anyway.
- A reference-style link definition that arrives later can restyle an already-committed paragraph. Note bodies don't use reference links, so this is accepted.
- `incrementalRendering` keeps redraw cost acceptable on a live region close to the terminal height.
- Ink's live region of `rows - 1` leaves the draft on the top row, because the cursor sits on the last row.

## Success Criteria (Summary)

- `cd tui && pnpm test && pnpm typecheck && pnpm lint` green after every phase.
- In a real terminal, a long conversation, a long streaming reply, a long draft, and a long note all stay within the screen without overdrawing the frame; history is reachable by touchpad.
- `/approve` leaves no scrollback of the approved conversation.
