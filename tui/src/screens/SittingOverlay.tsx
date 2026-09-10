import { Box, Text, useInput } from "ink";
import type { JSX } from "react";
import { useEffect } from "react";
import type { Grade } from "../api/sittings.js";
import { useSittingStore } from "../store/sitting.js";

const GRADES: Grade[] = ["forgot", "hard", "good", "easy"];
const GRADE_LABELS = ["1 Forgot", "2 Hard", "3 Good", "4 Easy"];

function renderOpening(): JSX.Element {
  return <Text>Loading...</Text>;
}

function renderNothingDue(): JSX.Element {
  return <Text>nothing_due</Text>;
}

function renderPresented(
  front: string | null,
  back: string | null,
  isBackVisible: boolean,
  selectedGradeIndex: number,
): JSX.Element {
  return (
    <Box flexDirection="column" gap={1}>
      {front !== null && <Text>{front}</Text>}
      {isBackVisible && back !== null && <Text>{back}</Text>}
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
  return <Text>complete</Text>;
}

function renderError(): JSX.Element {
  return <Text>error</Text>;
}

export default function SittingOverlay(): JSX.Element {
  const phase = useSittingStore((s) => s.phase);
  const front = useSittingStore((s) => s.front);
  const back = useSittingStore((s) => s.back);
  const isBackVisible = useSittingStore((s) => s.isBackVisible);
  const selectedGradeIndex = useSittingStore((s) => s.selectedGradeIndex);
  const open = useSittingStore((s) => s.open);
  const toggleBack = useSittingStore((s) => s.toggleBack);
  const moveSelection = useSittingStore((s) => s.moveSelection);
  const submitGrade = useSittingStore((s) => s.submitGrade);

  useEffect(() => {
    void open();
  }, [open]);

  useInput((input, key) => {
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
      body = renderError();
      break;
  }

  return (
    <Box flexDirection="column" flexGrow={1}>
      {body}
    </Box>
  );
}
