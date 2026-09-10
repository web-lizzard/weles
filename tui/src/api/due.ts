import { client } from "./client.js";

export type DuePartition = {
  total: number;
  notYetSeen: number;
  seenStillOwed: number;
  ripeOutsideSitting: number;
};

export async function fetchDueCount(): Promise<DuePartition> {
  const { data, error } = await client.GET("/due-cards/count");
  if (error || !data?.due) {
    throw new Error("Failed to fetch due count");
  }
  const { due } = data;
  return {
    total: due.total,
    notYetSeen: due.not_yet_seen,
    seenStillOwed: due.seen_still_owed,
    ripeOutsideSitting: due.ripe_outside_sitting,
  };
}
