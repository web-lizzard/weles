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

export const useDueStore = create<DueState & DueActions>((set, get) => ({
  partition: null,
  isStale: false,
  fetchDue: async () => {
    try {
      const partition = await fetchDueCount();
      set({ partition, isStale: false });
    } catch {
      set({ isStale: true });
    }
  },
  applyPartition: (partition) => set({ partition, isStale: false }),
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
