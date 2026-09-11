import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DuePartition } from "../src/api/due";
import { openSitting } from "../src/api/sittings";
import SittingOverlay from "../src/screens/SittingOverlay";
import { useDueStore } from "../src/store/due";
import { useAppStore } from "../src/store/index";
import { useSittingStore } from "../src/store/sitting";

vi.mock("../src/api/sittings", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/sittings")>();
  return {
    ...actual,
    openSitting: vi.fn(),
    revealBack: vi.fn(),
    gradeCard: vi.fn(),
    rejectCard: vi.fn(),
    currentCard: vi.fn(),
  };
});

const sittingId = "00000000-0000-4000-8000-000000000001";
const cardId = "00000000-0000-4000-8000-000000000101";

function resetSittingStore() {
  useSittingStore.setState({
    phase: "opening",
    sittingId: null,
    cardId: null,
    front: null,
    back: null,
    isBackVisible: false,
    selectedGradeIndex: 0,
    isSubmitting: false,
    error: null,
    lastAction: null,
    isResumed: false,
    outstandingCount: 0,
    notice: null,
  });
}

describe("SittingOverlay due breakdown", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useAppStore.setState({ isSittingOverlayOpen: true });
    resetSittingStore();
    useDueStore.setState({ partition: null, isStale: false });
    vi.mocked(openSitting).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function openWithOutstandingCount(outstandingCount: number) {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "Front line",
      sittingComplete: false,
      outstandingCount,
    });
    const rendered = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);
    return rendered;
  }

  it("shows the due-store total in the footer and no breakdown when only not_yet_seen is non-zero", async () => {
    const partition: DuePartition = {
      total: 3,
      notYetSeen: 3,
      seenStillOwed: 0,
      ripeOutsideSitting: 0,
    };
    useDueStore.setState({ partition, isStale: false });

    const { lastFrame } = await openWithOutstandingCount(99);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("3 cards due");
    expect(frame).toContain("Deck-wide due total");
    expect(frame).not.toMatch(/\d+ left/i);
    expect(frame).not.toMatch(/graded, still in this review/i);
    expect(frame).not.toMatch(/not yet shown in this review/i);
  });

  it("shows non-zero seen_still_owed and ripe_outside_sitting buckets beneath the total when a sitting is live", async () => {
    const partition: DuePartition = {
      total: 5,
      notYetSeen: 2,
      seenStillOwed: 1,
      ripeOutsideSitting: 2,
    };
    useDueStore.setState({ partition, isStale: false });

    const { lastFrame } = await openWithOutstandingCount(1);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("5 cards due");
    expect(frame).not.toContain("Why waiting:");
    expect(frame).toMatch(/2 not yet shown in this review/i);
    expect(frame).toMatch(/1 graded, still in this review/i);
    expect(frame).toMatch(/2 due outside this review/i);
  });

  it("reads the footer total from dueStore rather than sittingStore outstandingCount", async () => {
    const partition: DuePartition = {
      total: 4,
      notYetSeen: 4,
      seenStillOwed: 0,
      ripeOutsideSitting: 0,
    };
    useDueStore.setState({ partition, isStale: false });

    const { lastFrame } = await openWithOutstandingCount(7);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("4 cards due");
    expect(frame).not.toContain("7 left");
  });
});
