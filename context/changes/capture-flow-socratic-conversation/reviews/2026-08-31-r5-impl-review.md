# Impl review r5

reviewed at bbbb8dd

- **change-id**: capture-flow-socratic-conversation
- **scope**: phase 10-13 (TUI vertical slice — data layer, chat screen — per explicit request)
- **date**: 2026-08-31

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: NEEDS ATTENTION** (more than two WARNING dimensions)

## Success Criteria run

- `cd tui && pnpm typecheck` — `tsc --noEmit`, no output, exit 0
- `cd tui && pnpm test` — `vitest run`: `Test Files 4 passed (4)`, `Tests 11 passed (11)`

## Findings

### R5-F1 — WARNING

- **Dimension**: Plan Adherence (DRIFT)
- **Location**: `tui/src/screens/CaptureScreen.tsx:1,118-121`
- **Evidence:** citation — `context/changes/capture-flow-socratic-conversation/plan.md:654` requires: "`<Static items={transcript}>` renders each finalized `{role, content}` line — items here must stay append-only/immutable, never reordered or mutated, per Ink's `Static` contract." The file no longer imports `Static` at all (`CaptureScreen.tsx:1` — `import { Box, Text, useStdout } from "ink";`) and renders the transcript with a plain array map instead: `CaptureScreen.tsx:118-121` — `{transcript.map((entry, index) => (` / `// biome-ignore lint/suspicious/noArrayIndexKey: append-only transcript entries have no stable id` / `<TranscriptLine key={index} entry={entry} />` / `))}`. The `Static` wiring was present as committed for Phase 13 (`276bd89`) and was removed by a later commit (`663dfad`, `feat(tui): polish capture screen branding and chat labels`) that is not scoped to any phase's Changes Required. `proof-test skipped: would require new test infrastructure` — `ink-testing-library`'s captured frame does not expose Ink's internal Static-vs-reconciled render-count distinction (confirmed empirically: a probe test asserting the transcript re-renders less under `Static` than under `.map()` has no existing harness to observe that difference without instrumenting Ink's renderer, which the existing test suite does not do).
- **Fix:** `CaptureScreen`'s finalized transcript must render through Ink's `<Static items={transcript}>`, not a plain `.map()` — this is what keeps already-printed conversation history out of the per-frame reconciliation loop that every streamed delta otherwise re-triggers, per the plan's explicit Contract.

### R5-F2 — WARNING

- **Dimension**: Scope Discipline
- **Location**: `tui/src/screens/CaptureScreen.tsx:6-62`
- **Evidence:** citation — Phase 13's Contract (`plan.md:648-654`) names exactly four elements for `CaptureScreen.tsx`: `useEffect`-driven `initSession()`, `<Static items={transcript}>`, the in-flight `<Text>{currentReply}</Text>` line, and `<TextInput>`. Commit `663dfad` (`feat(tui): polish capture screen branding and chat labels`) adds `WELES_TAGLINE`, `UserLabel`, `WelesAgentLabel`, `WelesBrand`, `TopicHeading`, and `shouldShowWelesBrand` (a terminal-row budget calculator) to that file — none named in any reviewed phase's Contract. The commit is attributed on `todos.md` row 13.4, a Manual Verification step ("Build and run the TUI CLI against the running backend; hold a real multi-turn conversation") whose own Contract requires no code change at all, and the commit's own message carries scope `tui`, not the change-id `capture-flow-socratic-conversation`, unlike every other commit on this plan.
- **Fix:** UI polish beyond a phase's Contract (branding, labels, layout budgeting) belongs in its own planned phase or a follow-up change, not folded into a Manual Verification step's commit — keep a verification step's commit, if any, limited to what verification actually requires.

### R5-F3 — WARNING

- **Dimension**: Pattern Consistency
- **Location**: `tui/src/api/stream.ts:28`, `tui/src/screens/CaptureScreen.tsx:10-80`
- **Evidence:** citation from two sibling files — `context/foundation/rules/code-ordering.md:5` states: "Within a file, the public interface comes first; private/internal helpers come last." `tui/src/api/stream.ts` declares the private, unexported `parseStreamEvent` (line 28) before the public, exported `startCaptureSession` (line 41) and `sendMessage` (line 49). `tui/src/screens/CaptureScreen.tsx` declares six private, unexported helpers (`UserLabel`, `WelesAgentLabel`, `WelesBrand`, `TopicHeading`, `shouldShowWelesBrand`, `TranscriptLine`, lines 10-80) before the file's sole public export, `export default function CaptureScreen()` (line 82) — the `TranscriptLine` half of this ordering was already present in Phase 13's own commit (`276bd89`), not only the later polish commit. `code-ordering.md` is one of the plan's own cited references (`plan.md:696`).
- **Fix:** move each file's public/exported symbols above its private helpers — the private helpers may stay defined after their first use, per `code-ordering.md`'s own carve-out, but must not precede the public interface.

## Retractions

None.
