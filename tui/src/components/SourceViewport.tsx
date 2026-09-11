import { Box, Text } from "ink";
import type { JSX } from "react";

type SourceViewportProps = {
  lines: string[];
  offset: number;
  height: number;
};

const MORE_ABOVE = "more above";
const MORE_BELOW = "more below";

export default function SourceViewport({
  lines,
  offset,
  height,
}: SourceViewportProps): JSX.Element {
  const windowLines = lines.slice(offset, offset + height);
  const showMoreAbove = offset > 0;
  const showMoreBelow = offset + height < lines.length;

  return (
    <Box flexDirection="column">
      {showMoreAbove && <Text dimColor>{MORE_ABOVE}</Text>}
      {windowLines.map((line, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: viewport window is rebuilt each render
        <Text key={`${offset + index}`}>{line.length > 0 ? line : " "}</Text>
      ))}
      {showMoreBelow && <Text dimColor>{MORE_BELOW}</Text>}
    </Box>
  );
}
