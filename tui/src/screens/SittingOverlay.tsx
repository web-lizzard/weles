import { Box, Text, useInput, useStdout } from "ink";
import type { JSX } from "react";
import { useEffect, useState } from "react";
import type { CardSource, Grade } from "../api/sittings.js";
import DueOverlayFooter from "../components/DueOverlayFooter.js";
import SourceViewport from "../components/SourceViewport.js";
import { useDueStore } from "../store/due.js";
import { useAppStore } from "../store/index.js";
import { useSittingStore } from "../store/sitting.js";

const GRADES: Grade[] = ["forgot", "hard", "good", "easy"];
const GRADE_LABELS = ["1 Forgot", "2 Hard", "3 Good", "4 Easy"];
const ESC_HINT = "← ESC to go back";
const TOGGLE_CARD_HINT = "Press t to toggle card";
const REJECT_HINT = "Press x to turn down this card";
const REJECT_CONFIRM_HINT = "Turn down this card? y confirm · n cancel";
const SOURCE_HINT = "Press s to view source";
const RESUMED_BANNER = "Resumed — picking up where you left off";

const INVERSE_ON = "\u001b[7m";
const INVERSE_OFF = "\u001b[27m";
const DEFAULT_TERMINAL_ROWS = 24;
/** Rows reserved for overlay chrome outside the source viewport window. */
const SOURCE_VIEWPORT_CHROME_ROWS = 19;

type SourceViewState = {
  source: CardSource;
  isExpanded: boolean;
  offset: number;
};

export default function SittingOverlay(): JSX.Element {
  const { stdout } = useStdout();
  const sourceViewportHeight = sourceViewportLineCount(stdout.rows);
  const phase = useSittingStore((s) => s.phase);
  const front = useSittingStore((s) => s.front);
  const back = useSittingStore((s) => s.back);
  const isBackVisible = useSittingStore((s) => s.isBackVisible);
  const selectedGradeIndex = useSittingStore((s) => s.selectedGradeIndex);
  const toggleBack = useSittingStore((s) => s.toggleBack);
  const moveSelection = useSittingStore((s) => s.moveSelection);
  const submitGrade = useSittingStore((s) => s.submitGrade);
  const rejectCurrentCard = useSittingStore((s) => s.rejectCurrentCard);
  const error = useSittingStore((s) => s.error);
  const retry = useSittingStore((s) => s.retry);
  const sittingId = useSittingStore((s) => s.sittingId);
  const cardId = useSittingStore((s) => s.cardId);
  const isResumed = useSittingStore((s) => s.isResumed);
  const outstandingCount = useSittingStore((s) => s.outstandingCount);
  const notice = useSittingStore((s) => s.notice);
  const cardSource = useSittingStore((s) => s.cardSource);
  const isCardSourceProbeComplete = useSittingStore(
    (s) => s.isCardSourceProbeComplete,
  );
  const partition = useDueStore((s) => s.partition);
  const dueIsStale = useDueStore((s) => s.isStale);
  const [isRejectConfirmPending, setRejectConfirmPending] = useState(false);
  const [sourceView, setSourceView] = useState<SourceViewState | null>(null);
  const [sourceOpenRequested, setSourceOpenRequested] = useState(false);

  const isSourceAvailable = isCardSourceProbeComplete && cardSource !== null;

  useEffect(() => {
    void useSittingStore.getState().open();
  }, []);

  // biome-ignore lint/correctness/useExhaustiveDependencies: clear source UI when the card changes
  useEffect(() => {
    setSourceOpenRequested(false);
    setSourceView(null);
  }, [cardId]);

  useEffect(() => {
    if (!isBackVisible) {
      setRejectConfirmPending(false);
      setSourceView(null);
    }
  }, [isBackVisible]);

  useEffect(() => {
    if (
      !sourceOpenRequested ||
      !isSourceAvailable ||
      cardSource === null ||
      sourceView !== null
    ) {
      return;
    }
    setSourceView({
      source: cardSource,
      isExpanded: false,
      offset: 0,
    });
    setSourceOpenRequested(false);
  }, [sourceOpenRequested, isSourceAvailable, cardSource, sourceView]);

  useInput((input, key) => {
    if (sourceView !== null) {
      if (key.escape) {
        setSourceView(null);
        return;
      }

      if (input === "e") {
        setSourceView((current) => {
          if (current === null) {
            return current;
          }
          const nextExpanded = !current.isExpanded;
          const lines = buildSourceLines(current.source, nextExpanded);
          return {
            ...current,
            isExpanded: nextExpanded,
            offset: offsetToKeepSpanInView(
              current.source,
              lines,
              sourceViewportHeight,
              nextExpanded,
            ),
          };
        });
        return;
      }

      const lines = buildSourceLines(sourceView.source, sourceView.isExpanded);
      const maxOffset = Math.max(0, lines.length - sourceViewportHeight);

      if (key.upArrow) {
        setSourceView((current) =>
          current === null
            ? current
            : { ...current, offset: Math.max(0, current.offset - 1) },
        );
        return;
      }

      if (key.downArrow) {
        setSourceView((current) =>
          current === null
            ? current
            : {
                ...current,
                offset: Math.min(maxOffset, current.offset + 1),
              },
        );
        return;
      }

      if (key.pageUp) {
        setSourceView((current) =>
          current === null
            ? current
            : {
                ...current,
                offset: Math.max(0, current.offset - sourceViewportHeight),
              },
        );
        return;
      }

      if (key.pageDown) {
        setSourceView((current) =>
          current === null
            ? current
            : {
                ...current,
                offset: Math.min(
                  maxOffset,
                  current.offset + sourceViewportHeight,
                ),
              },
        );
        return;
      }

      return;
    }

    if (key.escape) {
      if (isRejectConfirmPending) {
        setRejectConfirmPending(false);
        return;
      }
      useAppStore.getState().closeSittingOverlay();
      useSittingStore.getState().reset();
      return;
    }

    if (phase === "error") {
      if (input === "r") {
        void retry();
      }
      return;
    }

    if (phase !== "presented") {
      return;
    }

    if (isRejectConfirmPending) {
      if (input === "y") {
        setRejectConfirmPending(false);
        void rejectCurrentCard();
        return;
      }
      if (input === "n") {
        setRejectConfirmPending(false);
        return;
      }
      return;
    }

    if (input === "s" && isBackVisible) {
      if (isSourceAvailable && cardSource !== null) {
        setSourceView({
          source: cardSource,
          isExpanded: false,
          offset: 0,
        });
      } else if (!isCardSourceProbeComplete) {
        setSourceOpenRequested(true);
      }
      return;
    }

    if (input === "t") {
      void toggleBack();
      return;
    }

    if (input === "x" && isBackVisible) {
      setRejectConfirmPending(true);
      return;
    }

    const digit = Number(input);
    if (digit >= 1 && digit <= 4) {
      void submitGrade(GRADES[digit - 1]);
      return;
    }

    if (key.upArrow) {
      moveSelection(-1);
      return;
    }

    if (key.downArrow) {
      moveSelection(1);
      return;
    }

    if (key.return) {
      void submitGrade(GRADES[selectedGradeIndex]);
    }
  });

  let body: JSX.Element;
  switch (phase) {
    case "opening":
      body = renderOpening();
      break;
    case "nothing_due":
      body = renderNothingDue();
      break;
    case "presented":
      body =
        sourceView !== null
          ? renderSourceView(sourceView, sourceViewportHeight)
          : renderPresented(front, back, isBackVisible, selectedGradeIndex);
      break;
    case "complete":
      body = renderComplete();
      break;
    case "error":
      body =
        error !== null ? (
          renderError(error)
        ) : (
          <Text color="red">Unknown error</Text>
        );
      break;
  }

  const footer =
    sittingId !== null ? (
      <DueOverlayFooter
        partition={partition}
        outstandingCount={outstandingCount}
        isStale={dueIsStale}
        showToggleHint={phase === "presented" && sourceView === null}
        toggleHint={TOGGLE_CARD_HINT}
        showRejectHint={
          phase === "presented" && isBackVisible && sourceView === null
        }
        rejectHint={REJECT_HINT}
        showRejectConfirm={
          phase === "presented" && isBackVisible && isRejectConfirmPending
        }
        rejectConfirmHint={REJECT_CONFIRM_HINT}
        showSourceHint={
          phase === "presented" &&
          isBackVisible &&
          isSourceAvailable &&
          sourceView === null
        }
        sourceHint={SOURCE_HINT}
      />
    ) : null;

  const presentedTopMargin = phase === "presented" ? (isResumed ? 2 : 1) : 1;

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text dimColor>{ESC_HINT}</Text>
      {phase === "presented" && isResumed && sourceView === null && (
        <Box marginTop={1}>
          <Text color="cyan">{RESUMED_BANNER}</Text>
        </Box>
      )}
      <Box
        flexDirection="column"
        flexGrow={1}
        marginTop={presentedTopMargin}
        gap={notice !== null ? 1 : 0}
      >
        {notice !== null && sourceView === null && (
          <Text dimColor>{notice}</Text>
        )}
        {body}
      </Box>
      {footer}
    </Box>
  );
}

function sourceViewportLineCount(stdoutRows: number): number {
  const rows = stdoutRows > 0 ? stdoutRows : DEFAULT_TERMINAL_ROWS;
  return Math.max(1, rows - SOURCE_VIEWPORT_CHROME_ROWS);
}

function visibleSourceBlocks(
  source: CardSource,
  isExpanded: boolean,
): CardSource["blocks"] {
  if (isExpanded) {
    return [...source.blocks].sort((a, b) => a.index - b.index);
  }
  const spanIndex = source.span.blockIndex;
  return source.blocks
    .filter(
      (block) => block.index >= spanIndex - 1 && block.index <= spanIndex + 1,
    )
    .sort((a, b) => a.index - b.index);
}

function blockToHighlightedLines(
  block: { index: number; text: string },
  span: CardSource["span"],
): string[] {
  let text = block.text;
  if (block.index === span.blockIndex) {
    text =
      text.slice(0, span.start) +
      INVERSE_ON +
      text.slice(span.start, span.end) +
      INVERSE_OFF +
      text.slice(span.end);
  }
  return text.split("\n");
}

function buildSourceLines(source: CardSource, isExpanded: boolean): string[] {
  const blocks = visibleSourceBlocks(source, isExpanded);
  return blocks.flatMap((block) => blockToHighlightedLines(block, source.span));
}

function spanLineIndexInLines(source: CardSource, isExpanded: boolean): number {
  const blocks = visibleSourceBlocks(source, isExpanded);
  let lineIndex = 0;

  for (const block of blocks) {
    if (block.index === source.span.blockIndex) {
      const beforeSpan = block.text.slice(0, source.span.start);
      return lineIndex + beforeSpan.split("\n").length - 1;
    }
    lineIndex += blockToHighlightedLines(block, source.span).length;
  }

  return 0;
}

function offsetToKeepSpanInView(
  source: CardSource,
  lines: string[],
  height: number,
  isExpanded: boolean,
): number {
  const spanLineIndex = spanLineIndexInLines(source, isExpanded);
  const maxOffset = Math.max(0, lines.length - height);
  if (spanLineIndex >= maxOffset) {
    return maxOffset;
  }
  return Math.min(spanLineIndex, maxOffset);
}

function renderSourceView(state: SourceViewState, height: number): JSX.Element {
  const lines = buildSourceLines(state.source, state.isExpanded);
  return <SourceViewport lines={lines} offset={state.offset} height={height} />;
}

function renderOpening(): JSX.Element {
  return <Text>Loading...</Text>;
}

function renderNothingDue(): JSX.Element {
  return <Text>Nothing due for review.</Text>;
}

function renderPresented(
  front: string | null,
  back: string | null,
  isBackVisible: boolean,
  selectedGradeIndex: number,
): JSX.Element {
  return (
    <Box flexDirection="column" gap={1}>
      {front !== null && (
        <Box flexDirection="column">
          <Text bold dimColor>
            Front
          </Text>
          <Text>{front}</Text>
        </Box>
      )}
      {isBackVisible && back !== null && (
        <Box flexDirection="column">
          <Text bold dimColor>
            Back
          </Text>
          <Text>{back}</Text>
        </Box>
      )}
      <Box flexDirection="column">
        {GRADE_LABELS.map((label, index) => (
          <Text
            key={label}
            color={index === selectedGradeIndex ? "blue" : undefined}
          >
            {label}
          </Text>
        ))}
      </Box>
    </Box>
  );
}

function renderComplete(): JSX.Element {
  return <Text>Sitting complete</Text>;
}

function renderError(error: { code: string; detail: string }): JSX.Element {
  return (
    <Box flexDirection="column" gap={1}>
      <Text color="red">{error.detail}</Text>
      <Text>Press r to retry.</Text>
    </Box>
  );
}
