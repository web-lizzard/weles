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

// Review evidence for finding R4-F1 (see context/changes/remember-flow-due-count/reviews/).
const STALE_POLL_PARTITION: DuePartition = {
  total: 5,
  notYetSeen: 5,
  seenStillOwed: 0,
  ripeOutsideSitting: 0,
};

const FRESH_GRADE_PARTITION: DuePartition = {
  total: 4,
  notYetSeen: 3,
  seenStillOwed: 1,
  ripeOutsideSitting: 0,
};

describe("dueStore poll/grade ordering", () => {
  beforeEach(() => {
    useDueStore.setState({ partition: null, isStale: false });
    vi.mocked(fetchDueCount).mockReset();
  });

  afterEach(() => {
    useDueStore.getState().stopPolling();
  });

  it("keeps the partition a grade response applied, rather than the reading an older in-flight poll returns", async () => {
    let resolvePoll!: (value: DuePartition) => void;
    const inFlightPoll = new Promise<DuePartition>((resolve) => {
      resolvePoll = resolve;
    });
    vi.mocked(fetchDueCount).mockReturnValue(inFlightPoll);

    // A poll leaves the client before the user grades a card.
    const pollDone = useDueStore.getState().fetchDue();

    // The grade response lands first and carries the newer partition.
    useDueStore.getState().applyPartition(FRESH_GRADE_PARTITION);
    expect(useDueStore.getState().partition).toEqual(FRESH_GRADE_PARTITION);

    // The poll that was already in flight now answers with its pre-grade reading.
    resolvePoll(STALE_POLL_PARTITION);
    await pollDone;

    expect(useDueStore.getState().partition).toEqual(FRESH_GRADE_PARTITION);
  });
});
