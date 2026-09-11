import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  currentCard,
  openSitting,
  rejectCard,
  SittingHttpError,
} from "../src/api/sittings";
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
const nextCardId = "00000000-0000-4000-8000-000000000102";

/** Retry must not re-issue a rejection the backend already recorded. */
describe("rejection retry", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Front",
      back: "Back",
      isBackVisible: true,
      selectedGradeIndex: 0,
      isSubmitting: false,
      error: null,
      lastAction: null,
      isResumed: false,
      outstandingCount: 1,
      notice: null,
    });
    vi.mocked(openSitting).mockReset();
    vi.mocked(rejectCard).mockReset();
    vi.mocked(currentCard).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not call rejectCard again when the rejection succeeded and only the re-read failed", async () => {
    vi.mocked(rejectCard).mockResolvedValue(undefined);
    vi.mocked(currentCard)
      .mockRejectedValueOnce(
        new SittingHttpError("upstream_unavailable", "Try again", 503),
      )
      .mockResolvedValue({
        sittingId,
        cardId: nextCardId,
        front: "Next after reject",
        sittingComplete: false,
        outstandingCount: 1,
      });

    await useSittingStore.getState().rejectCurrentCard();
    await vi.advanceTimersByTimeAsync(0);

    expect(useSittingStore.getState().phase).toBe("error");
    expect(rejectCard).toHaveBeenCalledTimes(1);

    await useSittingStore.getState().retry();
    await vi.advanceTimersByTimeAsync(0);

    expect(rejectCard).toHaveBeenCalledTimes(1);
    expect(useSittingStore.getState().phase).toBe("presented");
    expect(useSittingStore.getState().cardId).toBe(nextCardId);
  });
});
