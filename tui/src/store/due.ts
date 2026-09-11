import { create } from "zustand";
import { type DuePartition, fetchDueCount } from "../api/due.js";

type DueState = {
  partition: DuePartition | null;
  isStale: boolean;
};

type DueActions = {
  fetchDue: () => Promise<void>;
  applyPartition: (partition: DuePartition) => void;
  startPolling: (intervalMs: number) => void;
  stopPolling: () => void;
};

let pollIntervalId: ReturnType<typeof setInterval> | null = null;
let partitionGeneration = 0;

export const useDueStore = create<DueState & DueActions>((set, get) => ({
  partition: null,
  isStale: false,
  fetchDue: async () => {
    const generationAtStart = partitionGeneration;
    try {
      const partition = await fetchDueCount();
      if (generationAtStart !== partitionGeneration) {
        return;
      }
      set({ partition, isStale: false });
    } catch {
      if (generationAtStart !== partitionGeneration) {
        return;
      }
      set({ isStale: true });
    }
  },
  applyPartition: (partition) => {
    partitionGeneration += 1;
    set({ partition, isStale: false });
  },
  startPolling: (intervalMs: number) => {
    get().stopPolling();
    void get().fetchDue();
    pollIntervalId = setInterval(() => {
      void get().fetchDue();
    }, intervalMs);
  },
  stopPolling: () => {
    if (pollIntervalId !== null) {
      clearInterval(pollIntervalId);
      pollIntervalId = null;
    }
  },
}));
