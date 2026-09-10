import type { DuePartition } from "../api/due.js";

export function formatDueLine(total: number): string {
  const noun = total === 1 ? "card" : "cards";
  return `${total} ${noun} due`;
}

export function duePartitionShowsBreakdown(partition: DuePartition): boolean {
  return partition.seenStillOwed > 0 || partition.ripeOutsideSitting > 0;
}

export function formatDueBreakdownLines(partition: DuePartition): string[] {
  const lines: string[] = [];
  if (partition.notYetSeen > 0) {
    lines.push(`${partition.notYetSeen} not yet seen`);
  }
  if (partition.seenStillOwed > 0) {
    lines.push(`${partition.seenStillOwed} seen and still owed`);
  }
  if (partition.ripeOutsideSitting > 0) {
    lines.push(`${partition.ripeOutsideSitting} outside sitting`);
  }
  return lines;
}
