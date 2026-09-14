# TUI Capture Screen Fixes Implementation Plan

> Execution state lives in `todos.md` (sibling of this file) — see the plan skill's `references/todos-format.md`.

## Overview

Rebuild the TUI capture screen in the style of Claude Code's terminal UI, per the closed frame (`frame.md`, FR-01..FR-10):
- Conversation history moves into native terminal scrollback through Ink `<Static>`.
- A bounded live region holds the pinned draft, the conversation tail, the transient messages, the activity indicator, the input frame, and the status line.
- Markdown renders formatted in replies, the draft, and the note body.
- The notes and sitting overlays become bounded bottom panels that replace the input frame.
- `/approve` clears the screen and the terminal history.

## Current State Analysis

- **Shell.** `tui/src/app.tsx:54-94` renders a fixed `height={rows}` column. `CaptureScreen` sits inside a `rows-1` relative box, and the notes and sitting overlays are absolute full-screen boxes over it. The due line (`DueCountHeader`) is the last row, hidden while the sitting overlay is open (`app.tsx:96`).
- **Capture screen.** `tui/src/screens/CaptureScreen.tsx` stacks, top to bottom: brand, topic, receipt, the transcript box (unbounded, `:90`), the draft panel, the coverage banner, the error bar, and the input. The brand hides itself using a row budget that counts transcript *entries*, not wrapped rows (`:238-289`). Nothing constrains the total height, so long content overflows the frame.
- **Rendering.** Replies, the draft body (`:179`), and note blocks (`NoteDetailScreen.tsx:31-34`) print as plain `Text`. There is no markdown dependency (`tui/package.json`).
- **Store.** `tui/src/store/chat.ts`:
  - It clears the draft on every submit (`:67`) and on errors (`:81`, `:143-152`).
  - `approveDraft` wipes the transcript and starts a new session (`:178-188`).
  - `isStreaming` is set on submit and cleared in `finally` (`:65`, `:157`).
  - The screen uses `isStreaming` only to unfocus the input (`CaptureScreen.tsx:118`).
- **Panels.** Four screens and their keys:
  - `NoteListOverlay` and `CardListScreen` use ↑/↓ for selection.
  - `NoteDetailScreen` and `CardDetailScreen` leave ↑/↓ and PgUp/PgDn free.
  - `SittingOverlay` uses ↑/↓ for grade selection. Its source view scrolls with ↑/↓ and PgUp/PgDn through `SourceViewport`, with height `rows - SOURCE_VIEWPORT_CHROME_ROWS (19)` (`SittingOverlay.tsx:23-24`, `:336-339`).

  Key hints sit at the top (`← ESC to go back`) or in `DueOverlayFooter`.
- **Tests.** `ink-testing-library` fakes stdout with `columns = 100` and no `rows`, so every `rows > 0` check falls back to 24. No test asserts absolute positioning. The tests that depend on today's layout are:
  - the four "hides Weles brand …" tests in `test/captureScreen.test.tsx`;
  - `test/app.test.tsx:360`, the due row below the notes overlay;
  - `test/sittingOverlay.test.tsx:835`, which assumes a 5-line source window.

## Desired End State

- **Capture screen, top to bottom.**
  1. Terminal scrollback: brand, topic lines, and conversation that no longer fits.
  2. A live region of at most `rows - 1` lines:
     - the pinned draft region, while a draft exists;
     - the conversation tail, including the streaming reply formatted as markdown;
     - the transient coverage banner and stream error;
     - the activity indicator, while a turn is in flight;
     - `─` rule, input line, `─` rule;
     - the status line: the due line on the left, and `/approve` on the right while a draft exists.
- **Scrolling.** Touchpad scrolling reaches the history. The draft scrolls with ↑/↓.
- **Panels.** `/notes` and `/remember` replace the input frame and status line with a bottom panel. The panel is as tall as its content and at most `rows - 1` lines; overflow scrolls by keyboard, and key hints are on the panel's last line.
- **Approve.** `/approve` wipes the screen and scrollback, leaving the receipt and a focused frame.
- **Verification.** `cd tui && pnpm test && pnpm typecheck && pnpm lint`. Then run the TUI in a real terminal against a running backend (`pnpm --dir tui build && pnpm --dir tui start`) and go through the Manual steps in Phases 10, 12 and 14.

### Key Discoveries:

- **Clear-and-replay.** When a live frame is taller than the terminal, or shrinks back from full height, Ink writes `clearTerminal + fullStaticOutput + frame` (`tui/node_modules/ink/build/ink.js:89-112`, `:768`). A frame of exactly `rows` lines counts as fullscreen, and today's `app.tsx:54` renders exactly that. The live region must stay at `rows - 1` or fewer.
- **Static identity.** Changing the `<Static>` element identity (a new `key`) resets `fullStaticOutput` (`ink.js:324-327`, `reconciler.js:98-104`), so old history is never replayed. The remounted `<Static>` re-emits every item it receives, so it must receive only new items.
- **Wiping scrollback.** On non-Windows, `ansi-escapes` `clearTerminal` is `ESC[2J ESC[3J ESC[H` (`ansi-escapes/base.js:124-130`). Writing it through `useStdout().write` keeps log-update consistent (`ink.js:451-460`). Writing to `process.stdout` directly does not.
- **Resize.** `useStdout().stdout.rows` does not trigger a re-render on resize. `useWindowSize()` does (`ink/build/hooks/use-window-size.js`).
- **Render cost.** The default log-update rewrites the whole frame on every change (`log-update.js:45-52`). `render(..., { incrementalRendering: true })` rewrites only the changed lines, which matters for a live region close to the terminal height.
- **Text input keys.** `ink-text-input` ignores upArrow, downArrow, and tab (`ink-text-input/build/index.js:49-55`), so ↑/↓ reach a sibling `useInput`.
- **`useAnimation`.**
  - Signature: `useAnimation({ interval, isActive })` → `{ frame, time, delta, reset }` (`ink/build/hooks/use-animation.js:21-80`).
  - Vitest 3 fake timers also fake `performance.now()`.
- **Test harness.**
  - `lastFrame()` in `ink-testing-library` includes static output (debug mode writes `fullStaticOutput + output`, `ink.js:352-360`).
  - `rows` and `columns` can be overridden on the returned `stdout` with `Object.defineProperty`, followed by `rerender`.
- **`marked`.**
  - `marked` 18 is ESM with bundled types.
  - `marked.lexer` turns an unclosed fence into one `code` token that runs to the end of the input.
  - A top-level token is stable only when all of the following hold (0 changes over ~4,000 fuzzed docs):
    - it is not the last non-space token;
    - a blank line (`\n[ \t]*\n`) follows it;
    - if it is a `list`, the remaining text cannot be a list continuation, i.e. it does not match `/^(?:[ \t]|[-*+](?:[ \t]|$)|\d{1,9}(?:[.)](?:[ \t]|$))?$|\d{1,9}[.)])/`.
- **`wrap-ansi`.** Wrapped line counts equal screen rows only with `{ hard: true }`.
- **pnpm dependencies.** pnpm's strict layout hides Ink's transitive `chalk` and `wrap-ansi`, so both must be direct dependencies. `chalk@^5.6.2` shares Ink's copy.
- **Chalk in tests.** Chalk defaults to level 0 under vitest, so output contains no ANSI codes. Renderer unit tests pass `new Chalk({ level: 1 })` to assert styling.
- **Note markdown.** Note bodies use headings, `>` quotes, `-`/`+` bullets, ordered lists, bold, italic, and code spans (`backend/src/domain/distill/note_format.py:19-53`).

## What We're NOT Doing

- Backend, capture API, or SSE stream changes, and any change to what the agent says or drafts.
- Any change to the command set's semantics (`/approve`, `/notes`, `/remember`).
- Mouse or touchpad handling inside the app, and terminal mouse tracking.
- Interrupting an agent turn (no Esc-to-interrupt).
- An activity indicator in the notes or sitting panels; they keep their own loading states.
- Markdown formatting of flashcard fronts and backs.
- Re-wrapping scrollback after a terminal resize. History keeps its original wrap, and only the live region reflows.
- Diagnosing today's overlap separately. The new line budget replaces the code that causes it.

## Implementation Approach

A single pipeline turns everything conversational into screen lines:
- `renderConversationLines` combines the brand, the receipt, transcript entries (including topic markers), and the streaming reply.
- `renderMarkdownLines` formats and hard-wraps each piece to the terminal width.
- `splitStableBlocks` separates the finished part of a streaming reply from the block still being written.

`layoutCapture` is a pure function of rows, chrome height, draft lines, and conversation lines. It decides:
- how many lines are committed to history; this count only grows, and only lines from stable blocks can be committed;
- the draft window, capped at half the screen;
- the visible conversation tail;
- the filler rows that keep the draft pinned at the top.

`ConversationHistory` appends newly committed lines to a `<Static key={historyEpoch}>`. `/approve` increments `historyEpoch`: that remounts `<Static>`, and a layout effect writes the clear sequence.

Panels reuse the same idea with a shared bounded `BottomPanel` and a line window (`SourceViewport`).

The work goes bottom-up, one unit per pair of phases: pure libraries, then store, indicator, shell, draft, and panels. Each unit gets a stubs phase, then a behavior phase.

## Critical Implementation Details

- **Committing lines.** Only lines that already exist in `ConversationHistory`'s item list are committed. Pass `<Static>` a growing array, and on an epoch change pass an empty array along with the new key in the same commit. A remounted `<Static>` re-emits every item it is given.
- **Clearing the terminal.** Write the clear sequence from a layout effect keyed on `historyEpoch`, after the key change has committed. If the clear were written before the remount, Ink would replay the old `fullStaticOutput` on its next clear-and-replay.
- **Live region height.** Keep it at `rows - 1` or fewer at every step, including while a panel is open. At exactly `rows`, Ink switches to fullscreen mode, and leaving that mode clears the terminal and reprints all history.

## Phase 1: Markdown renderer stubs

### Overview

Add the markdown dependencies and put the renderer's exported signatures in place, with unimplemented bodies.

### Changes Required:

#### 1. Dependencies

**File**: `tui/package.json`

**Intent**: Make `marked`, `chalk`, and `wrap-ansi` importable under pnpm's strict layout.

**Contract**: `dependencies` gain `marked@^18`, `chalk@^5.6.2` (same copy as Ink), and `wrap-ansi@^10`. `pnpm-lock.yaml` is updated by `pnpm install`.

#### 2. Markdown module

**File**: `tui/src/lib/markdown.ts`

**Intent**: Declare the pure markdown surface that every later phase renders through.

**Contract**:
```ts
import type { ChalkInstance } from "chalk";
export type StableSplit = { stable: string; pending: string };
export function renderMarkdownLines(source: string, columns: number, chalk: ChalkInstance): string[];
export function splitStableBlocks(source: string): StableSplit;
```
Bodies throw `new Error("not implemented")`.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing suite stays green: `cd tui && pnpm test`

---

## Phase 2: Markdown renderer behavior

### Overview

Implement markdown-to-screen-lines rendering and the stable/pending split of a streaming reply.

### Changes Required:

#### 1. Rendering

**File**: `tui/src/lib/markdown.ts`

**Intent**: Replace raw markdown syntax with terminal styling in Claude Code's style, and return an exact array of screen rows.

**Contract**: `renderMarkdownLines` lexes `source` with `marked.lexer` and renders the tokens below. The output is wrapped with `wrap-ansi(…, columns, { hard: true })` and split on `\n`, so every element fits within `columns`. Empty input yields `[]`.

| Construct | Rendering |
| --- | --- |
| `heading` | bold; depth 1 is also underlined; no `#` |
| `strong` / `em` / `del` | bold / italic / strikethrough |
| `codespan` | colored |
| `code` | dim-indented block, with the fence markers removed; an unclosed fence renders the same way |
| `list` / `list_item` | `•` for bullets, `n.` for ordered items; nested items indented by two spaces; task items show `☐` or `☑` |
| `blockquote` | dim `│ ` prefix |
| `hr` | dim `─` rule of `columns` width |
| `link` | the text followed by a dim URL |
| `html`, `def` | raw text |

Blank lines separate blocks.

#### 2. Stable split

**File**: `tui/src/lib/markdown.ts`

**Intent**: Separate the prefix of a partial stream whose rendering will not change from the block still being written.

**Contract**: `splitStableBlocks(source)` returns `stable + pending === source`. `stable` is the concatenated `raw` of the longest run of top-level tokens that ends at a stable token. A token is stable when all of the following hold:
- it is not the last non-`space` token;
- the text from its start to the next non-space token contains `\n[ \t]*\n`;
- if it is a `list`, the remaining text does not match `/^(?:[ \t]|[-*+](?:[ \t]|$)|\d{1,9}(?:[.)](?:[ \t]|$))?$|\d{1,9}[.)])/`.

### Success Criteria:

#### Automated Verification:

- Markdown renderer tests pass: `cd tui && pnpm vitest run test/markdown.test.ts`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 3: Capture layout stubs

### Overview

Declare the pure line-budget function that decides what is committed to history, what the draft window shows, and what conversation tail stays live.

### Changes Required:

#### 1. Layout module

**File**: `tui/src/lib/captureLayout.ts`

**Intent**: One testable place for FR-02/FR-04/FR-08's height rules, so no component guesses row counts.

**Contract**:
```ts
export type CaptureLayoutInput = {
  rows: number;                 // terminal rows; live region budget is rows - 1
  chromeRows: number;           // indicator + transient messages + frame (3) + status line
  draftLines: string[] | null;  // null when no draft exists
  draftOffset: number;
  conversationLines: string[];  // all lines of the current epoch, oldest first
  stableLineCount: number;      // prefix of conversationLines eligible for history
  committedLineCount: number;   // lines already emitted to <Static>
};
export type CaptureLayout = {
  committedLineCount: number;   // never less than the input value
  draftWindow: { lines: string[]; offset: number; height: number; moreAbove: boolean; moreBelow: boolean } | null;
  conversationTail: string[];
  fillerRows: number;           // blank rows between tail and chrome while a draft is pinned
};
export function layoutCapture(input: CaptureLayoutInput): CaptureLayout;
export function clampDraftOffset(offset: number, draftLineCount: number, regionHeight: number): number;
```
Bodies throw `new Error("not implemented")`.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing suite stays green: `cd tui && pnpm test`

---

## Phase 4: Capture layout behavior

### Overview

Implement the line budget.

### Changes Required:

#### 1. Budget rules

**File**: `tui/src/lib/captureLayout.ts`

**Intent**: Enforce, for any content and terminal size, that the live region never exceeds `rows - 1` and never pushes the chrome off screen (FR-02, FR-08).

**Contract**:
- **Draft region height.** `draftHeight = min(draftLines.length + markerRows, floor((rows - 1) / 2))` when a draft exists, otherwise `0`. `markerRows` counts the `more above`/`more below` lines shown inside that height.
- **Draft offset.** `draftWindow.offset` equals `clampDraftOffset(draftOffset, draftLines.length, visible body height)`, which lies in `[0, max(0, length - height)]`.
- **Conversation space.** `space = max(0, rows - 1 - chromeRows - draftHeight)`.
- **Overflow.** `overflow = max(0, conversationLines.length - space)`.
- **Committed lines.** Output `committedLineCount = max(input.committedLineCount, min(overflow, stableLineCount))`.
- **Tail.** `conversationTail` is the last `space` lines of `conversationLines.slice(committedLineCount)`, so the head of an oversized in-progress block is hidden rather than committed.
- **Filler.** `fillerRows = space - conversationTail.length` while a draft exists, otherwise `0`.
- **Invariant.** `draftHeight + fillerRows + conversationTail.length + chromeRows <= rows - 1` whenever `rows - 1 >= chromeRows`.

### Success Criteria:

#### Automated Verification:

- Capture layout tests pass: `cd tui && pnpm vitest run test/captureLayout.test.ts`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 5: Chat store stubs

### Overview

Add the new store fields and the topic transcript entry type, with no behavior change.

### Changes Required:

#### 1. Store shape

**File**: `tui/src/store/chat.ts`

**Intent**: Give the shell an epoch to key history and clearing on, a turn start time for the indicator, and topic changes that have a place in the conversation stream.

**Contract**:
- `ChatState` gains `historyEpoch: number` (initial `0`) and `turnStartedAt: number | null` (initial `null`).
- `TranscriptEntry` becomes `{ role: "user" | "agent"; content: string } | { role: "topic"; content: string }`.
- Existing actions are unchanged in this phase.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing suite stays green: `cd tui && pnpm test`

---

## Phase 6: Chat store behavior

### Overview

Keep the draft pinned across redraft turns, advance the history epoch on approve, and record the turn start and topic changes.

### Changes Required:

#### 1. Draft persistence

**File**: `tui/src/store/chat.ts`

**Intent**: FR-08 requires the draft not to disappear while the conversation continues.

**Contract**:
- `sendUserMessage` no longer clears `draft` on submit.
- The first `draft_topic`, `draft_tag`, or `draft_delta` event of a turn replaces the previous draft with a fresh one. Later events of the same turn accumulate as today.
- `draft_done` replaces the draft as today.
- In-band and HTTP errors still clear the draft.

#### 2. Epoch, turn start, topic entries

**File**: `tui/src/store/chat.ts`

**Intent**: Drive history clearing (FR-07), the elapsed counter (FR-09), and the topic line in history.

**Contract**:
- `sendUserMessage` sets `turnStartedAt = Date.now()` together with `isStreaming: true`, and resets it to `null` in `finally`.
- A `done` event whose `topic` is non-null and differs from the current topic appends `{ role: "topic", content: topic }` after the agent entry.
- A successful `approveDraft` increments `historyEpoch` in the same `set` that clears the transcript.
- A failed approve leaves `historyEpoch` unchanged.

#### 3. Test rewrite

**File**: `tui/test/chat.test.ts`

**Intent**: The existing "clears draft when starting a new message" test asserts the behavior this phase removes.

**Contract**: That test is replaced by the pinned-draft behavior test. The other store tests stay unchanged.

### Success Criteria:

#### Automated Verification:

- Chat store tests pass: `cd tui && pnpm vitest run test/chat.test.ts`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 7: Activity indicator stubs

### Overview

Declare the activity indicator component and its pure helpers.

### Changes Required:

#### 1. Indicator helpers

**File**: `tui/src/lib/activityIndicator.ts`

**Intent**: Keep verb rotation and elapsed formatting pure and testable.

**Contract**:
```ts
export const INDICATOR_GLYPHS: readonly string[];   // e.g. "·", "✢", "✳", "✶", "✻", "✽"
export const INDICATOR_VERBS: readonly string[];    // e.g. "Pondering", "Distilling", "Weighing", …
export const VERB_INTERVAL_MS: number;              // 3000
export function indicatorVerb(elapsedMs: number): string;
export function formatElapsed(elapsedMs: number): string;  // "0s", "12s"
```

#### 2. Indicator component

**File**: `tui/src/components/ActivityIndicator.tsx`

**Intent**: The single animated line shown above the input frame during a turn.

**Contract**: `export default function ActivityIndicator({ startedAt }: { startedAt: number }): JSX.Element`. The body is unimplemented.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing suite stays green: `cd tui && pnpm test`

---

## Phase 8: Activity indicator behavior

### Overview

Implement the Claude Code-style thinking line: an animated glyph, a changing verb, and elapsed seconds (FR-09).

### Changes Required:

#### 1. Helpers

**File**: `tui/src/lib/activityIndicator.ts`

**Intent**: Make the verb and elapsed text depend only on the elapsed time.

**Contract**:
- `indicatorVerb(ms)` returns `INDICATOR_VERBS[floor(ms / VERB_INTERVAL_MS) % length]`.
- `formatElapsed(ms)` returns `${floor(ms / 1000)}s`.

#### 2. Component

**File**: `tui/src/components/ActivityIndicator.tsx`

**Intent**: Render `<glyph> <Verb>… (<n>s)`, with the glyph and verb in the accent color and the elapsed part dim.

**Contract**:
- The glyph comes from `useAnimation({ interval: 120 })` and cycles through `INDICATOR_GLYPHS`.
- Elapsed time is `Date.now() - startedAt`, re-read on each animation frame.
- The component renders exactly one row.

### Success Criteria:

#### Automated Verification:

- Activity indicator tests pass: `cd tui && pnpm vitest run test/activityIndicator.test.tsx`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

---

## Phase 9: Capture shell stubs

### Overview

Declare the components and the line pipeline of the new capture layout, and switch Ink to incremental rendering.

### Changes Required:

#### 1. Conversation lines

**File**: `tui/src/lib/conversationLines.ts`

**Intent**: Turn store state into the ordered screen lines that `layoutCapture` budgets.

**Contract**:
```ts
import type { ChalkInstance } from "chalk";
import type { TranscriptEntry } from "../store/chat.js";
export type ConversationLines = { lines: string[]; stableLineCount: number };
export function renderConversationLines(input: {
  showBrand: boolean;            // true in epoch 0
  showReceipt: boolean;          // approvalReceipt
  transcript: TranscriptEntry[];
  currentReply: string;
  columns: number;
  chalk: ChalkInstance;
}): ConversationLines;
```

#### 2. History, frame, status line

**File**: `tui/src/components/ConversationHistory.tsx`, `tui/src/components/InputFrame.tsx`, `tui/src/components/StatusLine.tsx`

**Intent**: Give each part of the Claude Code layout its own component.

**Contract**:
- `ConversationHistory({ epoch, lines }: { epoch: number; lines: string[] })` renders `<Static key={epoch} items={lines}>`.
- `InputFrame({ columns, children }: { columns: number; children: ReactNode })` renders a rule, the children row, and a rule.
- `StatusLine({ columns, showApproveHint }: { columns: number; showApproveHint: boolean })` renders the due line on the left and the `/approve` hint on the right.

#### 3. Terminal clear constant

**File**: `tui/src/lib/terminal.ts`

**Intent**: One named escape sequence for FR-07, with no direct `ansi-escapes` dependency.

**Contract**: `export const CLEAR_SCREEN_AND_SCROLLBACK = "\x1b[2J\x1b[3J\x1b[H";`

#### 4. Render options

**File**: `tui/src/cli.tsx`

**Intent**: Rewrite only changed lines of a tall live region.

**Contract**: `render(<App />, { incrementalRendering: true })`.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing suite stays green: `cd tui && pnpm test`

---

## Phase 10: Capture shell behavior

### Overview

Replace the fixed-height shell and the brand budget with scrollback history and a bounded live region. This phase covers FR-01, FR-02, FR-03, FR-04, FR-07, FR-09, FR-10, and FR-05 for replies. The draft stays unbounded at the top of the live region until Phase 12.

### Changes Required:

#### 1. Line pipeline

**File**: `tui/src/lib/conversationLines.ts`

**Intent**: Render everything conversational through markdown, so replies are formatted both while streaming and once complete.

**Contract**:
- **Line order:**
  1. brand (2 lines, when `showBrand`);
  2. receipt (thick rule plus `✓ Approved — queued for saving`, when `showReceipt`);
  3. each transcript entry: user as `🧑 You: ` plus the text; agent as `🦉 Weles: ` plus the first line, then `renderMarkdownLines`; topic as a bold `Topic: <topic>`;
  4. `currentReply`, rendered after `splitStableBlocks`.
- **Stable lines.** `stableLineCount` counts every line except those of `currentReply`'s pending block.

#### 2. Capture screen

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Lay out the history and live region per FR-01..FR-04, FR-09 and FR-10.

**Contract**:
- **Terminal size.** Rows and columns come from `useWindowSize()`.
- **Chrome.** `chromeRows` counts the indicator (1 while `isStreaming`), the coverage banner and stream error (their wrapped rows), the frame (3), and the status line (1).
- **Committed lines.** The screen keeps `committedLineCount` in state, reset to `0` when `historyEpoch` changes. It passes `lines.slice(0, committedLineCount)` to `ConversationHistory`.
- **Live region order.** Draft (temporary), `conversationTail`, banner, error, `ActivityIndicator` (while `turnStartedAt !== null`), `InputFrame` around `UserLabel` and `TextInput`, then `StatusLine` with `showApproveHint = draft !== null`.
- **Approve clear.** A `useLayoutEffect` on `historyEpoch > 0` writes `CLEAR_SCREEN_AND_SCROLLBACK` through `useStdout().write`.
- **Removed.** `shouldShowWelesBrand` and the `WelesBrand`, `TopicHeading`, and `ApprovalReceiptPanel` blocks are deleted.

#### 3. Shell

**File**: `tui/src/app.tsx`

**Intent**: Drop the fixed `height={rows}` shell. The due line now lives in `StatusLine`.

**Contract**:
- `App` renders `CaptureScreen` with no height constraint and no longer renders `DueCountHeader` directly.
- The overlays stay as they are, rendered after the capture screen, until Phase 14.

#### 4. Tests rewritten

**File**: `tui/test/captureScreen.test.tsx`, `tui/test/app.test.tsx`

**Intent**: Remove assertions tied to the removed brand budget and the old shell row.

**Contract**:
- The four "hides Weles brand …" tests are deleted.
- `app.test.tsx:348` ("partition total in a footer row below the capture screen") asserts that the due line appears after the lower frame rule.
- Command, stream, and draft-content tests stay unchanged.

### Success Criteria:

#### Automated Verification:

- Capture screen tests pass: `cd tui && pnpm vitest run test/captureScreen.test.tsx`
- Full TUI suite passes: `cd tui && pnpm test`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

#### Manual Verification:

With the backend running, run `pnpm --dir tui build && pnpm --dir tui start` in a real terminal (not the IDE's output pane).
- **Long conversation.** Exchange enough turns to exceed the terminal height. Earlier turns scroll into the terminal's history with the touchpad, and the input frame and status line never move or get overdrawn.
- **Streaming reply.** Ask for a long markdown reply (a heading, a list, a code block). It renders formatted while streaming, the tail stays visible above the frame, and the activity indicator with its rotating verb and seconds shows until the turn ends.
- **Approve.** Once a draft exists, `/approve` shows on the right of the status line. After `/approve`, touchpad scrollback holds nothing from the approved conversation; only the receipt and a focused frame remain.

---

## Phase 11: Draft region stubs

### Overview

Declare the pinned draft region and its line rendering.

### Changes Required:

#### 1. Draft lines

**File**: `tui/src/lib/draftLines.ts`

**Intent**: Render the draft (topic, tags, markdown body) into screen lines the layout can window.

**Contract**:
```ts
import type { ChalkInstance } from "chalk";
import type { Draft } from "../store/chat.js";
export function renderDraftLines(draft: Draft, columns: number, chalk: ChalkInstance): string[];
```

#### 2. Draft region component

**File**: `tui/src/components/DraftRegion.tsx`

**Intent**: The windowed, keyboard-scrolled draft at the top of the live region.

**Contract**: `export default function DraftRegion({ window }: { window: NonNullable<CaptureLayout["draftWindow"]> }): JSX.Element`. The body is unimplemented.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing suite stays green: `cd tui && pnpm test`

---

## Phase 12: Draft region behavior

### Overview

Pin the draft at the top of the visible screen with its own ↑/↓ scroll, and let the conversation flow out under it into history (FR-08, FR-05 draft body).

### Changes Required:

#### 1. Draft lines and region

**File**: `tui/src/lib/draftLines.ts`, `tui/src/components/DraftRegion.tsx`

**Intent**: Format the draft and show only its window.

**Contract**:
- `renderDraftLines` produces, in order: `Topic: <topic>` (yellow label, bold value), `Tags: a · b (new)`, a dim rule, then `renderMarkdownLines(content)`.
- `DraftRegion` renders a dim `more above` marker when needed, the window lines, a dim `more below` marker when needed, and a dim rule under the region. It is exactly `window.height` rows tall.

#### 2. Capture screen wiring

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Replace the temporary unbounded draft with the budgeted region.

**Contract**:
- **Layout inputs.** `layoutCapture` receives `draftLines = draft ? renderDraftLines(...) : null` and the screen's `draftOffset` state.
- **Arrows.** While a draft exists and no panel is open, `useInput` maps ↑ to `offset - 1` and ↓ to `offset + 1`, clamped through `clampDraftOffset`.
- **Offset reset.** `draftOffset` resets to `0` when a new draft replaces the old one.
- **Filler.** `fillerRows` blank rows are rendered between the tail and the chrome, so the draft's first row is the first row of the screen whenever the view is at the bottom.
- **Removed.** `DraftNotePanel` and `DraftTags` are deleted.

#### 3. Tests rewritten

**File**: `tui/test/captureScreen.test.tsx`

**Intent**: Update the draft rendering tests to the new region.

**Contract**: The "renders topic and tags …", "renders the draft body …" and "marks a newly minted tag distinctly …" tests keep their content assertions against the region's output.

### Success Criteria:

#### Automated Verification:

- Capture screen tests pass: `cd tui && pnpm vitest run test/captureScreen.test.tsx`
- Full TUI suite passes: `cd tui && pnpm test`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

#### Manual Verification:

With the backend running, run `pnpm --dir tui build && pnpm --dir tui start`.
- **Pinned draft.** Converse until the agent drafts a note longer than half the terminal. The draft sits at the top of the screen, and ↑/↓ scroll only the draft.
- **Redraft.** Ask for a redraft. The previous draft stays pinned until the new one starts, and the reply streams between the draft and the frame, with older lines disappearing under the draft.
- **History scroll.** Scroll back with the touchpad. The draft moves with the screen and is back at the top on returning to the bottom.

---

## Phase 13: Bottom panel stubs

### Overview

Declare the bounded bottom panel, and let the capture screen show a panel in place of its frame.

### Changes Required:

#### 1. Panel container and sizing

**File**: `tui/src/components/BottomPanel.tsx`, `tui/src/lib/panelLayout.ts`

**Intent**: One container for the notes and sitting panels: bounded height, content, then the hint line last.

**Contract**:
```ts
export default function BottomPanel({ hints, children }: { hints: string; children: ReactNode }): JSX.Element;
export const PANEL_CHROME_ROWS: number;  // top rule + hint line
export function panelBodyHeight(rows: number, reservedRows: number): number;  // max(1, rows - 1 - PANEL_CHROME_ROWS - reservedRows)
```

#### 2. Panel slot

**File**: `tui/src/screens/CaptureScreen.tsx`, `tui/src/app.tsx`

**Intent**: The panel replaces the input frame and status line inside the same live region.

**Contract**:
- `CaptureScreen` accepts `{ panel: ReactNode | null }`.
- `App` computes the panel element (notes list, detail, card list, card detail, or sitting) and passes it in, instead of rendering absolute overlays. Unimplemented pieces keep the current rendering until Phase 14.

### Success Criteria:

#### Automated Verification:

- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`
- Existing suite stays green: `cd tui && pnpm test`

---

## Phase 14: Bottom panels behavior

### Overview

Notes and sitting open as bounded bottom panels covering the input, with keyboard scroll for overflowing content and key hints at the bottom (FR-06). The note body is formatted as markdown (FR-05).

### Changes Required:

#### 1. Panel host

**File**: `tui/src/screens/CaptureScreen.tsx`, `tui/src/app.tsx`, `tui/src/components/BottomPanel.tsx`

**Intent**: The input and status line are neither shown nor focused while a panel is open; the conversation above stays in place.

**Contract**:
- While `panel !== null`, `CaptureScreen` renders the conversation tail and then `panel`, and omits the indicator, frame, and status line. The conversation budget uses the panel's rendered height as `chromeRows`.
- `BottomPanel` renders a dim top rule, the children, and the dim `hints` line.
- The absolute overlay boxes in `app.tsx` are removed.

#### 2. Panel screens

**File**: `tui/src/screens/NoteListOverlay.tsx`, `tui/src/screens/NoteDetailScreen.tsx`, `tui/src/screens/CardListScreen.tsx`, `tui/src/screens/CardDetailScreen.tsx`, `tui/src/screens/SittingOverlay.tsx`

**Intent**: Bound each screen's body to `panelBodyHeight` and scroll overflow by keyboard without reassigning existing keys.

**Contract**:

| Screen | Scrolling | Hint line |
| --- | --- | --- |
| `NoteListOverlay`, `CardListScreen` | The window follows the selection (↑/↓ unchanged), and PgUp/PgDn move the selection by a window | `↑↓ select · Enter open · ← ESC to go back`, with the existing wording kept |
| `NoteDetailScreen` | Renders `renderMarkdownLines` of the note blocks into a `SourceViewport`; ↑/↓ scroll by line, PgUp/PgDn by page | Tab and Esc hints |
| `CardDetailScreen` | Front, back, and anchor go into a `SourceViewport`; ↑/↓ scroll by line | `Enter jump to source · ← back` |
| `SittingOverlay` (presented phase) | Front and back go into a `SourceViewport`; PgUp/PgDn scroll it (↑/↓ keep grade selection) | Hints move to the last line |

- **Note anchor.** An anchor opens `NoteDetailScreen` scrolled so that the anchored block is the first visible line, replacing the current block filter.
- **Sitting source view.** Its height uses `panelBodyHeight` in place of `SOURCE_VIEWPORT_CHROME_ROWS`.
- **Due line.** The status line (due line) is hidden while any panel is open. The sitting panel keeps its due footer.

#### 3. Tests rewritten

**File**: `tui/test/app.test.tsx`, `tui/test/sittingOverlay.test.tsx`, `tui/test/noteDetailScreen.test.tsx`

**Intent**: Update the tests that assume full-screen overlays or the fixed 19-row chrome.

**Contract**:
- `app.test.tsx:360` ("keeps the due-count row visible below the notes overlay") is replaced by the panel test that hides the status line.
- `sittingOverlay.test.tsx:835` recomputes the scroll steps from `panelBodyHeight(24, …)`.
- The anchored-block tests in `noteDetailScreen.test.tsx:171,184` assert that the anchored block is the first visible line.

### Success Criteria:

#### Automated Verification:

- Panel tests pass: `cd tui && pnpm vitest run test/app.test.tsx test/noteDetailScreen.test.tsx test/sittingOverlay.test.tsx`
- Full TUI suite passes: `cd tui && pnpm test`
- Type check passes: `cd tui && pnpm typecheck`
- Lint passes: `cd tui && pnpm lint`

#### Manual Verification:

With the backend running, run `pnpm --dir tui build && pnpm --dir tui start`.
- **Notes panel.** `/notes` opens a panel at the bottom that replaces the input frame and status line, and the conversation above stays where it was. Open a long note: the body is formatted and scrolls with ↑/↓ inside a panel no taller than the terminal. Esc twice brings back the focused input frame.
- **Sitting panel.** `/remember` with due cards opens the sitting panel at the bottom. A long card back scrolls with PgUp/PgDn, and `s` opens the source view, which also stays within the terminal height.
- **Resize.** Resize the terminal while a panel is open. The panel reflows and never exceeds the terminal height.

---

## Testing Strategy

### Unit Tests:

- **Pure functions.** Markdown rendering and the stable split (`test/markdown.test.ts`, using `new Chalk({ level: 1 })` for styling assertions), the line budget (`test/captureLayout.test.ts`), and the indicator helpers (`test/activityIndicator.test.tsx`).
- **Store transitions.** `test/chat.test.ts`: draft persistence, epoch, turn start, topic entries.
- **Component behavior** through `ink-testing-library`:
  - Tests override `rows`/`columns` on the returned `stdout` and `rerender`.
  - `lastFrame()` includes `<Static>` output, so history content and order are assertable.
  - Timers are faked with `vi.useFakeTimers()`.

### Integration Tests:

- None beyond App-level Ink tests (`test/app.test.tsx`), because the API boundary stays mocked through `vi.mock("../src/api/*")`.

### Manual Testing Steps:

1. Run a long capture conversation in a real terminal. Check that touchpad scrollback reaches the earlier turns and that the frame never gets overdrawn.
2. Stream a long markdown reply. Check that it is formatted progressively, that the tail stays visible, and that the indicator ticks.
3. Get a long draft. Check that it is pinned at the top, scrolls with ↑/↓, and survives a redraft turn.
4. Run `/approve`. Check that the screen and scrollback are cleared and that the receipt and a focused frame remain.
5. Open `/notes` and a long note, and run `/remember` with a long card. Check that each panel is bounded, scrolls by keyboard, has its hints at the bottom, and brings back the input on close.

## Performance Considerations

- **Frame rewrites.** The live region can approach the terminal height, so `incrementalRendering: true` limits each keystroke's rewrite to the changed lines.
- **Markdown re-lexing.** Markdown is re-lexed on every streamed delta. Replies are short enough for that, but memoize the stable prefix's rendered lines by `(stable, columns)` so only the pending block is re-rendered per delta.

## Migration Notes

- Adds the direct dependencies `marked`, `chalk`, and `wrap-ansi` to `tui/package.json`.
- No data or API migration.
- History is not re-wrapped on resize, which is an accepted behavior.

## References

- Frame: `context/changes/tui-capture-screen-fixes/frame.md`, `frame-log.md`
- Ink internals: `tui/node_modules/ink/build/ink.js:89-112,324-327,451-460,752-798`, `components/Static.js`, `hooks/use-animation.js`, `hooks/use-window-size.js`
- Current layout: `tui/src/app.tsx:54-96`, `tui/src/screens/CaptureScreen.tsx:87-121,238-289`, `tui/src/store/chat.ts:58-196`
- Scroll precedent: `tui/src/components/SourceViewport.tsx:7-29`, `tui/src/screens/SittingOverlay.tsx:97-177,336-339`
- Archived `/approve` contract: `context/archive/changes/2026-09-02-capture-flow-review-approve-outbox/plan.md:888`
