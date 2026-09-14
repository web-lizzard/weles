import { Box, Text } from "ink";
import type { JSX, ReactNode } from "react";

type InputFrameProps = {
  columns: number;
  children: ReactNode;
};

export default function InputFrame({
  columns,
  children,
}: InputFrameProps): JSX.Element {
  const rule = "─".repeat(columns > 0 ? columns : 1);

  return (
    <Box flexDirection="column">
      <Text dimColor>{rule}</Text>
      <Box>{children}</Box>
      <Text dimColor>{rule}</Text>
    </Box>
  );
}
