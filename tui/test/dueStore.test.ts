import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DuePartition } from "../src/api/due";
import { fetchDueCount } from "../src/api/due";
import { useDueStore } from "../src/store/due";

vi.mock("../src/api/due", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/due")>();
  return {
    ...actual,
    fetchDueCount: vi.fn(),
  };
});

const PARTITION: DuePartition = {
  total: 4,
  notYetSeen: 1,
  seenStillOwed: 2,
  ripeOutsideSitting: 1,
};

const OTHER_PARTITION: DuePartition = {
  total: 9,
  notYetSeen: 3,
  seenStillOwed: 0,
  ripeOutsideSitting: 6,
};

function resetDueStore() {
  useDueStore.setState({ partition: null, isStale: false });
}

describe("useDueStore", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetDueStore();
    vi.mocked(fetchDueCount).mockReset();
  });

  afterEach(() => {
    useDueStore.getState().stopPolling();
    vi.useRealTimers();
  });

  it("fetches immediately on startPolling, then once per interval tick", async () => {
    vi.mocked(fetchDueCount).mockResolvedValue(PARTITION);

    useDueStore.getState().startPolling(15_000);
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchDueCount).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(15_000);
    expect(fetchDueCount).toHaveBeenCalledTimes(2);
  });

  it("stopPolling clears every interval started, not only the most recent one", async () => {
    vi.mocked(fetchDueCount).mockResolvedValue(PARTITION);

    useDueStore.getState().startPolling(1000);
    await vi.advanceTimersByTimeAsync(0);
    useDueStore.getState().startPolling(1000);
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchDueCount).toHaveBeenCalledTimes(2);

    useDueStore.getState().stopPolling();
    await vi.advanceTimersByTimeAsync(5000);

    expect(fetchDueCount).toHaveBeenCalledTimes(2);
  });

  it("sets isStale and leaves the last partition untouched when a fetch fails", async () => {
    useDueStore.setState({ partition: PARTITION, isStale: false });
    vi.mocked(fetchDueCount).mockRejectedValue(new Error("network down"));

    await useDueStore.getState().fetchDue();

    expect(useDueStore.getState().isStale).toBe(true);
    expect(useDueStore.getState().partition).toEqual(PARTITION);
  });

  it("clears isStale and replaces the partition on a successful fetch", async () => {
    useDueStore.setState({ partition: PARTITION, isStale: true });
    vi.mocked(fetchDueCount).mockResolvedValue(OTHER_PARTITION);

    await useDueStore.getState().fetchDue();

    expect(useDueStore.getState().isStale).toBe(false);
    expect(useDueStore.getState().partition).toEqual(OTHER_PARTITION);
  });

  it("applyPartition writes the partition and clears isStale without a network call", () => {
    useDueStore.setState({ partition: PARTITION, isStale: true });

    useDueStore.getState().applyPartition(OTHER_PARTITION);

    expect(fetchDueCount).not.toHaveBeenCalled();
    expect(useDueStore.getState().partition).toEqual(OTHER_PARTITION);
    expect(useDueStore.getState().isStale).toBe(false);
  });
});
