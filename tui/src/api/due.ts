import { getClient } from "./instance.js";

export type DuePartition = {
  total: number;
  notYetSeen: number;
  seenStillOwed: number;
  ripeOutsideSitting: number;
};

type DuePartitionRaw = {
  total: number;
  not_yet_seen: number;
  seen_still_owed: number;
  ripe_outside_sitting: number;
};

export function toDuePartition(due: DuePartitionRaw): DuePartition {
  return {
    total: due.total,
    notYetSeen: due.not_yet_seen,
    seenStillOwed: due.seen_still_owed,
    ripeOutsideSitting: due.ripe_outside_sitting,
  };
}

export async function fetchDueCount(): Promise<DuePartition> {
  const { data, error } = await getClient().GET("/due-cards/count");
  if (error || !data?.due) {
    throw new Error("Failed to fetch due count");
  }
  return toDuePartition(data.due);
}
