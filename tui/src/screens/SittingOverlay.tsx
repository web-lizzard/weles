import { Box, Text, useInput } from "ink";
import type { JSX } from "react";
import { useEffect } from "react";
import type { Grade } from "../api/sittings.js";
import { useAppStore } from "../store/index.js";
import { useSittingStore } from "../store/sitting.js";

const GRADES: Grade[] = ["forgot", "hard", "good", "easy"];
const GRADE_LABELS = ["1 Forgot", "2 Hard", "3 Good", "4 Easy"];
const ESC_HINT = "← ESC to go back";
const TOGGLE_CARD_HINT = "Press t to toggle card";
const RESUMED_BANNER = "Resumed — picking up where you left off";

export default function SittingOverlay(): JSX.Element {
  const phase = useSittingStore((s) => s.phase);
  const front = useSittingStore((s) => s.front);
  const back = useSittingStore((s) => s.back);
  const isBackVisible = useSittingStore((s) => s.isBackVisible);
  const selectedGradeIndex = useSittingStore((s) => s.selectedGradeIndex);
  const toggleBack = useSittingStore((s) => s.toggleBack);
  const moveSelection = useSittingStore((s) => s.moveSelection);
  const submitGrade = useSittingStore((s) => s.submitGrade);
  const error = useSittingStore((s) => s.error);
  const retry = useSittingStore((s) => s.retry);
  const sittingId = useSittingStore((s) => s.sittingId);
  const isResumed = useSittingStore((s) => s.isResumed);
  const outstandingCount = useSittingStore((s) => s.outstandingCount);
  const notice = useSittingStore((s) => s.notice);

  useEffect(() => {
    void useSittingStore.getState().open();
  }, []);

  useInput((input, key) => {
    if (key.escape) {
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

    if (input === "t") {
      void toggleBack();
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
      <Box flexDirection="column">
        <Text color="yellow">{outstandingCount} left</Text>
        {phase === "presented" && (
          <Text color="yellow">{TOGGLE_CARD_HINT}</Text>
        )}
      </Box>
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
