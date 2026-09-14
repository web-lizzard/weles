import { Box, Text, useStdout } from "ink";
import type { JSX } from "react";
import type { CaptureLayout } from "../lib/captureLayout.js";

const DEFAULT_TERMINAL_COLUMNS = 80;
const MORE_ABOVE_TEXT = "↑ more above";
const MORE_BELOW_TEXT = "↓ more below";

type DraftRegionProps = {
  window: NonNullable<CaptureLayout["draftWindow"]>;
};

export default function DraftRegion({ window }: DraftRegionProps): JSX.Element {
  const { stdout } = useStdout();
  const columns =
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS;
  const rule = "─".repeat(columns > 0 ? columns : 1);

  return (
    <Box flexDirection="column">
      {window.moreAbove && <Text dimColor>{MORE_ABOVE_TEXT}</Text>}
      {window.lines.map((line, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: the window has no stable id
        <Text key={index}>{line}</Text>
      ))}
      {window.moreBelow && <Text dimColor>{MORE_BELOW_TEXT}</Text>}
      <Text dimColor>{rule}</Text>
    </Box>
  );
}
