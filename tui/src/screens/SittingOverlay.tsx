import { Box, Text, useInput } from "ink";
import type { JSX } from "react";
import { useEffect, useState } from "react";
import type { CardSource, Grade } from "../api/sittings.js";
import DueOverlayFooter from "../components/DueOverlayFooter.js";
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
const EXPAND_SOURCE_HINT = "Press e to expand to the whole note";
const RESUMED_BANNER = "Resumed — picking up where you left off";

type SourceViewState = {
  source: CardSource;
  isExpanded: boolean;
  offset: number;
};

export default function SittingOverlay(): JSX.Element {
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
  const isResumed = useSittingStore((s) => s.isResumed);
  const outstandingCount = useSittingStore((s) => s.outstandingCount);
  const notice = useSittingStore((s) => s.notice);
  const partition = useDueStore((s) => s.partition);
  const dueIsStale = useDueStore((s) => s.isStale);
  const [isRejectConfirmPending, setRejectConfirmPending] = useState(false);
  const [sourceView, setSourceView] = useState<SourceViewState | null>(null);
  const [isSourceAvailable, setIsSourceAvailable] = useState(false);

  const closeSourceView = (): void => {};

  const openSourceView = (): void => {};

  const probeSourceAvailability = async (): Promise<void> => {};

  const toggleSourceExpanded = (): void => {};

  const moveSourceOffset = (_delta: number): void => {};

  const phase8SourceScaffold = {
    sourceView,
    isSourceAvailable,
    hints: { source: SOURCE_HINT, expand: EXPAND_SOURCE_HINT },
    handlers: {
      closeSourceView,
      openSourceView,
      probeSourceAvailability,
      toggleSourceExpanded,
      moveSourceOffset,
    },
    setters: { setSourceView, setIsSourceAvailable },
  };
  void phase8SourceScaffold;

  useEffect(() => {
    void useSittingStore.getState().open();
  }, []);

  useEffect(() => {
    if (!isBackVisible) {
      setRejectConfirmPending(false);
    }
  }, [isBackVisible]);

  useInput((input, key) => {
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
      body = renderPresented(front, back, isBackVisible, selectedGradeIndex);
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
        showToggleHint={phase === "presented"}
        toggleHint={TOGGLE_CARD_HINT}
        showRejectHint={phase === "presented" && isBackVisible}
        rejectHint={REJECT_HINT}
        showRejectConfirm={
          phase === "presented" && isBackVisible && isRejectConfirmPending
        }
        rejectConfirmHint={REJECT_CONFIRM_HINT}
      />
    ) : null;

  const presentedTopMargin = phase === "presented" ? (isResumed ? 2 : 1) : 1;

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text dimColor>{ESC_HINT}</Text>
      {phase === "presented" && isResumed && (
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
        {notice !== null && <Text dimColor>{notice}</Text>}
        {body}
      </Box>
      {footer}
    </Box>
  );
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
