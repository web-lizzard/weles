import type { JSX } from "react";

type ConversationHistoryProps = {
  epoch: number;
  lines: string[];
};

export default function ConversationHistory(
  _props: ConversationHistoryProps,
): JSX.Element {
  throw new Error("not implemented");
}
