---
status: closed
created: 2026-09-13
updated: 2026-09-14
---

## Boundaries

In scope: the layout of the TUI capture screen (`tui/src/screens/CaptureScreen.tsx`) and the shell that hosts it (`tui/src/app.tsx`) — where the conversation, the input, the draft note, the notes and sitting panels, and the flashcard/due information sit relative to each other, how each behaves once its content outgrows the space it has, how markdown in agent output is displayed, the activity indicator while the agent is working, and the hint shown while a draft note is on screen.

Design reference: Claude Code's terminal UI. Where this frame does not settle a visual or interaction detail, the behaviour closest to Claude Code is the expected one.

Out of scope: the backend, the capture API and its SSE stream; what the agent says or drafts; the command set's semantics (what approving a note does is unchanged); mouse or touchpad handling inside the app; interrupting an agent turn (no Esc-to-interrupt); activity indicators outside the capture conversation (notes and sitting panels keep their own loading states); markdown formatting of flashcard fronts and backs.

## Requirements

- **FR-01** — The user's input line sits at the bottom of the capture screen inside a frame: a horizontal rule directly above it and a horizontal rule directly below it.
- **FR-02** — Conversation content (user turns and agent replies, including a reply still streaming) fills the space above the input frame, top to bottom, and never overdraws the frame or anything rendered below it — for any transcript length, reply length, or terminal size.
- **FR-03** — Flashcard (due-count) information is a single status line directly below the input frame, in the position and styling Claude Code uses for its mode line (e.g. "auto mode on").
- **FR-04** — Conversation that no longer fits above the input frame is reachable by scrolling the terminal's own scrollback (mouse wheel, touchpad, or the terminal's scroll keys), the way Claude Code's history is; the capture screen defines no in-app scroll keys for it, and touchpad or wheel scrolling always scrolls that history, never a region inside the app.
- **FR-05** — Markdown is displayed formatted (headings, emphasis, lists, code) rather than as raw syntax in: agent replies, both once complete and progressively while still streaming; the draft note body; and the note body in the notes panel.
- **FR-06** — Opening notes (`/notes`) or a review sitting (`/remember`) shows its panel at the bottom of the screen in place of the input frame, the way Claude Code shows its dialogs: the panel covers the input (the input is neither shown nor accepts typing while the panel is open), it does not need to occupy the full terminal, the conversation above stays where it is, and the panel's navigation and key hints are at its bottom. A panel never grows taller than the terminal: content that does not fit (a long note body, a card, a source view) scrolls inside the panel with the keyboard. Closing the panel brings the input frame back.
- **FR-07** — After a successful `/approve`, the approved conversation is cleared from both the screen and the terminal's history (it can no longer be scrolled back to): what remains is the approval receipt and a fresh, focused input frame.
- **FR-08** — While a draft note exists, it is fixed at the top of the visible screen, above the conversation, and does not move as the conversation continues. The conversation (including redraft replies) runs between the draft and the input frame; lines that no longer fit there disappear under the draft into the terminal's history (FR-04), the way Claude Code's text leaves the screen. When the draft is longer than its region, it scrolls inside that region with the up and down arrow keys, independently of the conversation. The draft region never pushes the input frame, the activity indicator, or the status line off the screen. "Fixed" holds whenever the view is at the bottom of the terminal; while the user scrolls back through history with the touchpad (FR-04), the draft moves with the rest of the screen and is back in place on returning to the bottom.
- **FR-09** — From the moment the user submits a message until the agent's turn ends (completed, failed, or errored), an animated activity indicator in the style of Claude Code's thinking indicator is shown directly above the input frame: an animated glyph, a verb that changes while the turn runs, and the seconds elapsed since submit. It is gone once the turn has ended.
- **FR-10** — While a draft note is on screen, a hint that `/approve` approves the note is shown right-aligned on the status line below the input frame (FR-03); it is not shown when there is no draft.
