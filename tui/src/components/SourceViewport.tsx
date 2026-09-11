import { Text } from "ink";
import type { JSX } from "react";

type SourceViewportProps = {
  lines: string[];
  offset: number;
  height: number;
};

export default function SourceViewport({
  lines: _lines,
  offset: _offset,
  height: _height,
}: SourceViewportProps): JSX.Element {
  return <Text />;
}
