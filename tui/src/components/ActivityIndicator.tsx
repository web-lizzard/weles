import { Text, useAnimation } from "ink";
import type { JSX } from "react";
import {
  formatElapsed,
  INDICATOR_GLYPHS,
  indicatorVerb,
} from "../lib/activityIndicator";

type ActivityIndicatorProps = {
  startedAt: number;
};

export default function ActivityIndicator({
  startedAt,
}: ActivityIndicatorProps): JSX.Element {
  const { frame } = useAnimation({ interval: 100 });
  const glyph = INDICATOR_GLYPHS[frame % INDICATOR_GLYPHS.length];
  const elapsedMs = Date.now() - startedAt;

  return (
    <Text>
      <Text color="yellow">
        {glyph} {indicatorVerb(elapsedMs)}…
      </Text>
      <Text dimColor> ({formatElapsed(elapsedMs)})</Text>
    </Text>
  );
}
