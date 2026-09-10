import type { DuePartition } from "../api/due.js";

export function formatDueLine(total: number): string {
  const noun = total === 1 ? "card" : "cards";
  return `${total} ${noun} due`;
}

export function duePartitionShowsBreakdown(partition: DuePartition): boolean {
  return partition.seenStillOwed > 0 || partition.ripeOutsideSitting > 0;
}

export type DueBreakdownEntry = {
  key: "notYetSeen" | "seenStillOwed" | "ripeOutsideSitting";
  count: number;
  description: string;
};

export function dueBreakdownEntries(
  partition: DuePartition,
): DueBreakdownEntry[] {
  const entries: DueBreakdownEntry[] = [];
  if (partition.notYetSeen > 0) {
    entries.push({
      key: "notYetSeen",
      count: partition.notYetSeen,
      description: "not yet shown in this review",
    });
  }
  if (partition.seenStillOwed > 0) {
    entries.push({
      key: "seenStillOwed",
      count: partition.seenStillOwed,
      description: "graded, still in this review",
    });
  }
  if (partition.ripeOutsideSitting > 0) {
    entries.push({
      key: "ripeOutsideSitting",
      count: partition.ripeOutsideSitting,
      description: "due outside this review",
    });
  }
  return entries;
}

/** Shown under the total when the sitting overlay has no bucket breakdown. */
export const OVERLAY_DUE_TOTAL_HINT =
  "Deck-wide due total (same as the line below when you exit review).";
