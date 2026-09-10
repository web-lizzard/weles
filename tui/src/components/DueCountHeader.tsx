import { Text } from "ink";
import { formatDueLine } from "../lib/dueFormat.js";
import { useDueStore } from "../store/due.js";

export default function DueCountHeader() {
  const partition = useDueStore((state) => state.partition);
  const isStale = useDueStore((state) => state.isStale);

  if (partition === null) {
    return null;
  }

  return <Text dimColor={isStale}>{formatDueLine(partition.total)}</Text>;
}
