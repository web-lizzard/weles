import { Box, Text, useStdout } from "ink";
import type { JSX, ReactNode } from "react";

const DEFAULT_TERMINAL_COLUMNS = 80;

type BottomPanelProps = {
  hints: string;
  children: ReactNode;
};

export default function BottomPanel({
  hints,
  children,
}: BottomPanelProps): JSX.Element {
  const { stdout } = useStdout();
  const columns =
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS;
  const rule = "─".repeat(columns > 0 ? columns : 1);

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text dimColor>{rule}</Text>
      <Box flexDirection="column" flexGrow={1}>
        {children}
      </Box>
      <Text dimColor>{hints}</Text>
    </Box>
  );
}
