## Current State

Session closed. Everything is settled in frame.md (FR-01 to FR-10, with Boundaries). Nothing is open.

Handoff notes for `/plan`, not requirements:
- Ink clears the terminal and reprints all static output once live output exceeds the terminal height (`tui/node_modules/ink/build/ink.js:89-111`, `:768`). FR-02, FR-06 and FR-08 are what keep the live region within it.
- The diagnosis of today's overlap (`tui/src/screens/CaptureScreen.tsx:90`, `:278`) is parked (overlap-cause).
- FR-07 wipes terminal history as well. FR-06 retires the absolute full-screen overlays in `tui/src/app.tsx:57-94`.

## Log

### 2026-09-13 — capture-layout: Claude Code-style capture layout — ACCEPTED
Why: The user stated the layout directly: input at the bottom between top and bottom rules, agent output growing top-down above it, flashcard info below the frame. That matches today's intent — the due line is already a footer below the capture region (`tui/src/app.tsx:96`) — so it is a rearrangement of the same pieces, not a new feature.
Consequence: FR-01, FR-02 and FR-03 are written into frame.md.

### 2026-09-13 — scroll-mechanism: Native scrollback vs in-app viewport — OPEN
Why: "Scroll up" reads as either terminal-native scrollback (Ink `<Static>`) or a key-driven viewport. The two conflict differently with the absolute-positioned overlays over a fixed-height shell (`tui/src/app.tsx:54-94`), so the choice changes scope.

### 2026-09-13 — overlap-cause: What overlaps today and why — OPEN
Why: "Never overlaps the frame" is stated as a requirement but also implies an observed defect. Likely causes are an unconstrained transcript box (`tui/src/screens/CaptureScreen.tsx:90`) and a row budget that counts entries instead of wrapped rows (`CaptureScreen.tsx:278`). These are unconfirmed until the user describes what they saw.

### 2026-09-13 — pinned-vs-flowing: Placement of draft, banner, error, receipt, topic, brand — OPEN
Why: The requested layout names only the transcript, input and flashcard info. Six other blocks render between them today (`tui/src/screens/CaptureScreen.tsx:87-104`), and the draft panel in particular has a review-while-redrafting use that conflicts with scrolling away.

### 2026-09-13 — approve-hint: Right-aligned approve hint in draft mode — OPEN
Why: The command name the user gave (`/approved`) differs from the implemented and plan-fixed literal `/approve` (`tui/src/screens/CaptureScreen.tsx:14`). The hint's row is also unspecified.

### 2026-09-13 — scroll-mechanism: Native terminal scrollback, Claude Code style — ACCEPTED
Why: The user chose option (a) and stated the overall aim: the design should be as close to Claude Code as possible. Ink 7.1.1 ships `Static` (`tui/node_modules/ink/build/components/Static.d.ts`), so the mechanism is available without a new rendering stack.
Consequence: FR-04 is written, and Claude Code is recorded as the design reference in Boundaries. This opens overlay-model and approve-reset, because the fixed-height shell with absolute overlays (`tui/src/app.tsx:54-94`) and the transcript wipe on approve (`tui/src/store/chat.ts:178-188`) both assume a fully redrawable screen.
Supersedes: 2026-09-13 — scroll-mechanism — OPEN.

### 2026-09-13 — markdown-render: Render markdown in agent output — ACCEPTED
Why: The user reports the screen shows markdown unformatted. Nothing in the TUI interprets it: replies print as plain `Text` (`tui/src/screens/CaptureScreen.tsx:96-99`, `:298-301`), and there is no markdown dependency in `tui/package.json`. Notes are markdown by domain definition (`backend/src/domain/distill/note_format.py:19,53`), so raw syntax is expected content, not a backend defect.
Consequence: FR-05 covers completed replies. Streaming, draft body and the notes/cards screens are tracked as markdown-reach.

### 2026-09-13 — overlay-model: Notes and sitting overlays under native scrollback — OPEN
Why: Absolute overlays over a fixed-height shell (`tui/src/app.tsx:54-94`) cannot cover history that has been flushed to terminal scrollback. The choice is between inline panels in the live region (Claude Code) and alternate-screen full-screen views (`tui/node_modules/ink/build/render.d.ts:118`).

### 2026-09-13 — approve-reset: What happens to printed history after /approve — OPEN
Why: Today's reset wipes the transcript (`tui/src/store/chat.ts:183`). Under FR-04, text already in scrollback cannot be removed except by clearing the terminal.

### 2026-09-13 — tall-live-region: Streaming content taller than the terminal — OPEN
Why: FR-02 has to hold while a reply or draft is still live and exceeds the terminal height. Under FR-04 that content is not yet in scrollback.

### 2026-09-13 — overlay-model: Bottom panels in place of the input, Claude Code style — ACCEPTED
Why: The user said the overlay need not be full-screen, but it must cover the input, and they want notes/flashcard controls at the bottom as in Claude Code. This is option (i), inline panels in the live region. It fits FR-04 because nothing has to paint over flushed scrollback, unlike today's absolute full-screen overlays (`tui/src/app.tsx:57-94`). Alternate screen (option ii) is rejected along with it.
Consequence: FR-06 is written. This opens panel-height (the note body, cards and source view can exceed the terminal) and flashcard-row-under-panel.
Supersedes: 2026-09-13 — overlay-model — OPEN.

### 2026-09-13 — approve-reset: Clear the conversation after /approve, as today — ACCEPTED
Why: The user wants the current behaviour kept: the store wipes the transcript and starts a new session (`tui/src/store/chat.ts:178-188`). Under FR-04 that means actively clearing printed output rather than leaving it in scrollback.
Consequence: FR-07 is written. Whether terminal scrollback is also wiped is tracked as approve-clears-scrollback.
Supersedes: 2026-09-13 — approve-reset — OPEN.

### 2026-09-13 — markdown-reach: Markdown formatted while streaming — ACCEPTED
Why: The user chose the first sub-option: replies format progressively during the stream, as in Claude Code, accepting transient oddities such as a half-open code fence. Deltas accumulate into `currentReply` (`tui/src/store/chat.ts:72-75`), so the full partial text is available to render on each update.
Consequence: FR-05 is widened to include streaming. The draft body and the note/card panels remain open under the same idea-id.

### 2026-09-13 — pinned-vs-flowing: Draft in a fixed region with its own scroll, stream below — ACCEPTED
Why: The user wants the draft pinned with a separate scroll when it is long, and the normal agent stream beneath it. This resolves the tension raised earlier: the draft no longer scrolls away during redraft turns and no longer grows without bound.
Consequence: FR-08 is written without fixing the region's screen position. The literal "top" conflicts with FR-04 and is tracked as draft-position. The scroll keys are tracked as draft-scroll-keys. The other non-transcript blocks remain open.

### 2026-09-13 — draft-position: "Top" pin vs native scrollback — OPEN
Why: Under FR-04 only the bottom live region is redrawable, and `Static` output always lands above it (`tui/node_modules/ink/build/components/Static.d.ts`). A true top-of-terminal pin requires the fixed-height full-screen shell that FR-04 replaced (`tui/src/app.tsx:54-55`).

### 2026-09-14 — draft-position: Draft fixed at the top, conversation flows out under it — ACCEPTED
Why: The user described the draft as fixed at the top of the screen, with conversation text "flowing out from under it" like Claude Code's normal text once history no longer fits. That is compatible with FR-04 when the live region spans the visible terminal while a draft exists: draft on top, conversation tail, frame, flashcard row, with overflow lines flushed into scrollback above the draft. Option (b), a fixed full-screen shell, is not needed. The live region must not exceed the terminal height: at more than `viewportRows`, Ink clears the terminal and reprints all static output each frame (`tui/node_modules/ink/build/ink.js:89-111`, `:768`).
Consequence: FR-08 is rewritten to fix the position. The consequence that the draft scrolls away during a touchpad history scroll is tracked as draft-scrolls-away.
Supersedes: 2026-09-13 — draft-position — OPEN.

### 2026-09-14 — panel-height: Bounded bottom panels with in-panel keyboard scroll — ACCEPTED
Why: The user agreed that panels behave like the draft, bounded with inner scroll, but placed at the bottom and covering the input, the mirror of the draft's top placement. The source view already scrolls this way (`tui/src/components/SourceViewport.tsx:7-29`).
Consequence: FR-06 is extended.

### 2026-09-14 — scroll-routing: Touchpad scrolls terminal history, inner regions scroll by keyboard — ACCEPTED
Why: The user worried that the draft scroll and the history scroll would conflict, and asked whether Ink routes scrolling to where the cursor focus is. It does not: Ink parses no mouse or wheel input (`tui/node_modules/ink/build/parse-keypress.js`, no mouse handling; `hooks/` has no mouse hook). A touchpad scroll is consumed by the terminal emulator as scrollback and never reaches the app. Ink's focus (`hooks/use-focus.js`) is keyboard focus only. Routing the wheel into the app would require enabling terminal mouse tracking, which takes the touchpad away from native history, contradicting FR-04. The two scrolls therefore do not conflict when inner regions use keys.
Consequence: FR-04 now states that touchpad and wheel always scroll history. FR-06 and FR-08 state keyboard inner scroll. Mouse handling is out of scope. The key choice is tracked as draft-scroll-keys.

### 2026-09-14 — tall-live-region: Streaming content taller than its space — ACCEPTED
Why: This is resolved by FR-02 together with FR-08. The live conversation runs in the space between the draft (or screen top) and the frame, and lines that do not fit leave into scrollback, so the stream tail stays visible above the frame, as in Claude Code.
Consequence: No new requirement. The Ink clear-on-overflow behaviour (`ink.js:89-111`) is noted for the plan.
Supersedes: 2026-09-13 — tall-live-region — OPEN.

### 2026-09-14 — activity-indicator: Claude Code-style thinking indicator during agent turns — ACCEPTED
Why: The user asked for a loading indicator while the agent is working, as close to Claude Code's as possible. Today nothing on screen signals that a turn is in flight: `isStreaming` is set on submit and cleared when the stream ends (`tui/src/store/chat.ts:65`, `:157`), but the screen uses it only to unfocus the input (`tui/src/screens/CaptureScreen.tsx:118`). Before the first delta arrives the screen looks idle. Ink 7.1.1 ships an animation hook (`tui/node_modules/ink/build/hooks/use-animation.js`), so an animated indicator needs no new rendering stack.
Consequence: FR-09 is written, placed above the input frame as in Claude Code. The indicator's contents, including the interrupt question, are tracked as indicator-content; approve and panel loading as indicator-reach.

### 2026-09-14 — indicator-content: Rotating verb and elapsed seconds, no interrupt — ACCEPTED
Why: The user picked the changing verb and the seconds counter from Claude Code's indicator and dropped "esc to interrupt" for now. That keeps FR-09 purely presentational: no abort path has to be added to the stream loop (`tui/src/store/chat.ts:71`).
Consequence: FR-09 is extended. Interrupt is recorded as out of scope.
Supersedes: 2026-09-14 — indicator-content — OPEN (Current State thread).

### 2026-09-14 — indicator-reach: Indicator for capture conversation turns only — ACCEPTED
Why: The user said the indicator is mainly for the capture screen. Panels keep their existing loading states (e.g. `tui/src/screens/NoteDetailScreen.tsx:81`).
Consequence: The FR-09 wording (message submit to turn end) stands. Panel indicators are out of scope.

### 2026-09-14 — draft-scroll-keys: Up/down arrows scroll the draft — ACCEPTED
Why: The user chose up/down. These are free while the input is focused, because `ink-text-input` uses left/right for the cursor, and the capture screen has no prompt-history recall on up/down (`tui/src/screens/CaptureScreen.tsx:61-80`). The height cap follows from FR-02: the draft may not push the frame, indicator or status line off the screen.
Consequence: FR-08 is extended.

### 2026-09-14 — markdown-reach: Draft body and note body formatted too — ACCEPTED
Why: The user extended markdown rendering to the draft body and the note body. Both are markdown by domain definition (`backend/src/domain/distill/note_format.py:19,53`) and print raw today (`tui/src/screens/CaptureScreen.tsx:179`, `tui/src/screens/NoteDetailScreen.tsx:31-34`). Card fronts and backs were not requested (`tui/src/screens/CardDetailScreen.tsx:42-43`).
Consequence: FR-05 is widened. Card markdown is out of scope.

### 2026-09-14 — flashcard-info: Due line as a Claude Code-style status line below the input — ACCEPTED
Why: The user placed the flashcard line under the input, where Claude Code shows its mode line. The content stays the existing due line (`tui/src/components/DueCountHeader.tsx:13-16`). Only its position and style change.
Consequence: FR-03 is rewritten. Its visibility under open panels follows the Claude Code reference rule rather than a separate decision (closes flashcard-row-under-panel).

### 2026-09-14 — pinned-vs-flowing: Remaining blocks follow the Claude Code reference — ACCEPTED
Why: The draft is settled by FR-08. The user's repeated instruction to be as close to Claude Code as possible covers the topic heading, coverage banner, stream error, approval receipt and brand. The Boundaries reference rule already governs unsettled visual details, so separate requirements would restate it.
Consequence: No new requirement.

### 2026-09-14 — overlap-cause: Diagnosis deferred to the plan — PARKED
Why: FR-02, FR-04, FR-06 and FR-08 define the target state regardless of what overlaps today. Candidate causes (`tui/src/screens/CaptureScreen.tsx:90`, `:278`) and Ink's clear-on-overflow (`tui/node_modules/ink/build/ink.js:89-111`) are implementation concerns for `/plan`.

### 2026-09-14 — draft-scrolls-away: "Always pinned" conflicts with native scrollback — OPEN
Why: The user answered that the draft must always stay pinned to the top, rejecting the draft moving away during a touchpad history scroll. With history in terminal scrollback (FR-04), a touchpad scroll moves the whole screen and never reaches the app (`tui/node_modules/ink/build/parse-keypress.js`). Options (a) accept the move, (b) alternate screen while drafting, (c) draft out of the flow are laid out in Current State.

### 2026-09-14 — draft-scrolls-away: Draft pinned while at the bottom, moves during history scroll — ACCEPTED
Why: The user chose option (a). The draft is fixed whenever the view is at the bottom and moves with the screen only while scrolling back through history. This preserves FR-04; the alternate-screen option (b) would have lost touchpad history, and on many terminals collided with FR-08's up/down draft scroll.
Consequence: FR-08 now states the at-the-bottom qualification.
Supersedes: 2026-09-14 — draft-scrolls-away — OPEN.

### 2026-09-14 — approve-hint: `/approve` hint right-aligned on the status line — ACCEPTED
Why: The user confirmed the existing literal `/approve` (`tui/src/screens/CaptureScreen.tsx:14`). "/approved" was a slip, so there is no rename and the archived contract (`archive/changes/2026-09-02-capture-flow-review-approve-outbox/plan.md:888`) stands. Placement on the status line below the frame follows the proposal, which the user did not contest, and the Claude Code reference.
Consequence: FR-10 is written.
Supersedes: 2026-09-13 — approve-hint — OPEN.

### 2026-09-14 — approve-clears-scrollback: /approve clears screen and terminal history — ACCEPTED
Why: The user wants everything cleared, consistent with today's full transcript wipe (`tui/src/store/chat.ts:178-188`) now that the transcript lives in terminal scrollback.
Consequence: FR-07 is rewritten.
