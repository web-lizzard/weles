import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  gradeCard,
  openSitting,
  revealBack,
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
  };
});

const sittingId = "00000000-0000-4000-8000-000000000001";
const cardId = "00000000-0000-4000-8000-000000000101";
const nextCardId = "00000000-0000-4000-8000-000000000102";

function resetStore() {
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
  });
}

describe("useSittingStore", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetStore();
    vi.mocked(openSitting).mockReset();
    vi.mocked(revealBack).mockReset();
    vi.mocked(gradeCard).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("enters presented with a fresh card when openSitting returns an opened sitting", async () => {
    useSittingStore.setState({
      back: "stale back",
      isBackVisible: true,
      selectedGradeIndex: 3,
      error: { code: "old", detail: "old" },
    });
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "What is a SYN?",
      sittingComplete: false,
    });

    await useSittingStore.getState().open();
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(state.phase).toBe("presented");
    expect(state.sittingId).toBe(sittingId);
    expect(state.cardId).toBe(cardId);
    expect(state.front).toBe("What is a SYN?");
    expect(state.back).toBeNull();
    expect(state.isBackVisible).toBe(false);
    expect(state.selectedGradeIndex).toBe(0);
    expect(state.error).toBeNull();
  });

  it("enters nothing_due when openSitting reports an empty backlog", async () => {
    vi.mocked(openSitting).mockResolvedValue({ kind: "nothing_due" });

    await useSittingStore.getState().open();
    await vi.advanceTimersByTimeAsync(0);

    expect(useSittingStore.getState().phase).toBe("nothing_due");
    expect(useSittingStore.getState().cardId).toBeNull();
  });

  it("fetches the back only on the first flip to visible, then toggles without another request", async () => {
    vi.mocked(revealBack).mockResolvedValue({
      sittingId,
      cardId,
      front: "Front",
      back: "Back text",
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Front",
      isBackVisible: false,
    });

    await useSittingStore.getState().toggleBack();
    await vi.advanceTimersByTimeAsync(0);
    expect(revealBack).toHaveBeenCalledTimes(1);
    expect(useSittingStore.getState().isBackVisible).toBe(true);
    expect(useSittingStore.getState().back).toBe("Back text");

    await useSittingStore.getState().toggleBack();
    await vi.advanceTimersByTimeAsync(0);
    expect(revealBack).toHaveBeenCalledTimes(1);
    expect(useSittingStore.getState().isBackVisible).toBe(false);

    await useSittingStore.getState().toggleBack();
    await vi.advanceTimersByTimeAsync(0);
    expect(revealBack).toHaveBeenCalledTimes(1);
    expect(useSittingStore.getState().isBackVisible).toBe(true);
  });

  it("presents the next card after a grade and completes the sitting when no card remains", async () => {
    vi.mocked(gradeCard)
      .mockResolvedValueOnce({
        sittingId,
        sittingComplete: false,
        nextCardId,
        nextFront: "Next front",
      })
      .mockResolvedValueOnce({
        sittingId,
        sittingComplete: true,
        nextCardId: null,
        nextFront: null,
      });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "First front",
      selectedGradeIndex: 2,
    });

    await useSittingStore.getState().submitGrade("good");
    await vi.advanceTimersByTimeAsync(0);

    let state = useSittingStore.getState();
    expect(state.phase).toBe("presented");
    expect(state.cardId).toBe(nextCardId);
    expect(state.front).toBe("Next front");
    expect(state.selectedGradeIndex).toBe(0);
    expect(state.isBackVisible).toBe(false);

    await useSittingStore.getState().submitGrade("easy");
    await vi.advanceTimersByTimeAsync(0);

    state = useSittingStore.getState();
    expect(state.phase).toBe("complete");
    expect(state.cardId).toBeNull();
  });

  it("records a sitting HTTP error on failure and retry re-issues the same action", async () => {
    vi.mocked(openSitting)
      .mockRejectedValueOnce(
        new SittingHttpError("empty_sitting", "No cards due", 409),
      )
      .mockResolvedValueOnce({
        kind: "opened",
        sittingId,
        cardId,
        front: "Recovered",
        sittingComplete: false,
      });

    await useSittingStore.getState().open();
    await vi.advanceTimersByTimeAsync(0);

    expect(useSittingStore.getState().phase).toBe("error");
    expect(useSittingStore.getState().error).toEqual({
      code: "empty_sitting",
      detail: "No cards due",
    });
    expect(useSittingStore.getState().lastAction).toEqual({ type: "open" });

    await useSittingStore.getState().retry();
    await vi.advanceTimersByTimeAsync(0);

    expect(openSitting).toHaveBeenCalledTimes(2);
    expect(useSittingStore.getState().phase).toBe("presented");
    expect(useSittingStore.getState().front).toBe("Recovered");
  });
});
