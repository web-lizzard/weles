import { Static, Text } from "ink";
import type { JSX } from "react";

type ConversationHistoryProps = {
  epoch: number;
  lines: string[];
};

export default function ConversationHistory({
  epoch,
  lines,
}: ConversationHistoryProps): JSX.Element {
  return (
    <Static key={epoch} items={lines}>
      {(line, index) => <Text key={index}>{line}</Text>}
    </Static>
  );
}
