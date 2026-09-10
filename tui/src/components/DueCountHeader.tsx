import { Text } from "ink";
import { useDueStore } from "../store/due.js";

function formatDueLine(total: number): string {
  const noun = total === 1 ? "card" : "cards";
  return `${total} ${noun} due`;
}

export default function DueCountHeader() {
  const partition = useDueStore((state) => state.partition);
  const isStale = useDueStore((state) => state.isStale);

  if (partition === null) {
    return null;
  }

  return <Text dimColor={isStale}>{formatDueLine(partition.total)}</Text>;
}
