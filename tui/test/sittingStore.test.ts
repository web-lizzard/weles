import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DuePartition } from "../src/api/due";
import {
  currentCard,
  gradeCard,
  openSitting,
  rejectCard,
  revealBack,
  SITTING_EXPIRED,
  SittingHttpError,
} from "../src/api/sittings";
import { useDueStore } from "../src/store/due";
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

const DUE_PARTITION: DuePartition = {
  total: 5,
  notYetSeen: 2,
  seenStillOwed: 1,
  ripeOutsideSitting: 2,
};

function resetDueStore() {
  useDueStore.setState({ partition: null, isStale: false });
}

function resetStore() {
  useSittingStore.getState().reset();
}

describe("useSittingStore", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetDueStore();
    resetStore();
    vi.mocked(openSitting).mockReset();
    vi.mocked(revealBack).mockReset();
    vi.mocked(gradeCard).mockReset();
    vi.mocked(rejectCard).mockReset();
    vi.mocked(currentCard).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("pushes due from openSitting into dueStore on a successful open", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "What is a SYN?",
      sittingComplete: false,
      outstandingCount: 0,
      due: DUE_PARTITION,
    });

    await useSittingStore.getState().open();
    await vi.advanceTimersByTimeAsync(0);

    expect(useDueStore.getState().partition).toEqual(DUE_PARTITION);
    expect(useDueStore.getState().isStale).toBe(false);
  });

  it("pushes due from gradeCard into dueStore on a successful grade", async () => {
    const updatedDue: DuePartition = {
      total: 3,
      notYetSeen: 0,
      seenStillOwed: 2,
      ripeOutsideSitting: 1,
    };
    vi.mocked(gradeCard).mockResolvedValue({
      sittingId,
      outstandingCount: 1,
      sittingComplete: false,
      nextCardId,
      nextFront: "Next front",
      due: updatedDue,
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Front",
      selectedGradeIndex: 1,
    });
    useDueStore.setState({ partition: DUE_PARTITION, isStale: true });

    await useSittingStore.getState().submitGrade("hard");
    await vi.advanceTimersByTimeAsync(0);

    expect(useDueStore.getState().partition).toEqual(updatedDue);
    expect(useDueStore.getState().isStale).toBe(false);
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
      outstandingCount: 0,
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
        outstandingCount: 0,
        sittingComplete: false,
        nextCardId,
        nextFront: "Next front",
      })
      .mockResolvedValueOnce({
        sittingId,
        outstandingCount: 0,
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
        outstandingCount: 0,
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

  it("opens a sitting after reset while the previous openSitting call is still in flight", async () => {
    let resolveFirst: (value: Awaited<ReturnType<typeof openSitting>>) => void =
      () => {};
    const firstOpen = new Promise<Awaited<ReturnType<typeof openSitting>>>(
      (resolve) => {
        resolveFirst = resolve;
      },
    );
    vi.mocked(openSitting)
      .mockImplementationOnce(() => firstOpen)
      .mockResolvedValueOnce({
        kind: "opened",
        sittingId,
        cardId,
        front: "Second open",
        sittingComplete: false,
        outstandingCount: 0,
      });

    const first = useSittingStore.getState().open();
    useSittingStore.getState().reset();

    const second = useSittingStore.getState().open();
    await vi.advanceTimersByTimeAsync(0);

    resolveFirst({
      kind: "opened",
      sittingId,
      cardId,
      front: "Stale first open",
      sittingComplete: false,
      outstandingCount: 0,
    });
    await first;
    await second;
    await vi.advanceTimersByTimeAsync(0);

    expect(openSitting).toHaveBeenCalledTimes(2);
    expect(useSittingStore.getState().phase).toBe("presented");
    expect(useSittingStore.getState().front).toBe("Second open");
  });

  it("sets isResumed and outstandingCount when openSitting returns a resumed sitting", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "resumed",
      sittingId,
      cardId,
      front: "Resumed front",
      sittingComplete: false,
      outstandingCount: 3,
    });

    await useSittingStore.getState().open();
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(state.phase).toBe("presented");
    expect(state.isResumed).toBe(true);
    expect(state.outstandingCount).toBe(3);
  });

  it("clears isResumed and updates outstandingCount on the first grade after a resume", async () => {
    vi.mocked(gradeCard).mockResolvedValue({
      sittingId,
      outstandingCount: 2,
      sittingComplete: false,
      nextCardId,
      nextFront: "Next front",
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Resumed front",
      isResumed: true,
      outstandingCount: 3,
    });

    await useSittingStore.getState().submitGrade("good");
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(state.isResumed).toBe(false);
    expect(state.outstandingCount).toBe(2);
  });

  it("re-opens once with a notice when gradeCard returns sitting_expired instead of entering error", async () => {
    vi.mocked(gradeCard).mockRejectedValue(
      new SittingHttpError(SITTING_EXPIRED, "Sitting no longer offered", 409),
    );
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId: "00000000-0000-4000-8000-000000000002",
      cardId,
      front: "Fresh front",
      sittingComplete: false,
      outstandingCount: 1,
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Stale front",
    });

    await useSittingStore.getState().submitGrade("good");
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(state.phase).not.toBe("error");
    expect(state.error).toBeNull();
    expect(state.notice).toMatch(/expired/i);
    expect(openSitting).toHaveBeenCalledTimes(1);
    expect(state.front).toBe("Fresh front");
    expect(state.outstandingCount).toBe(1);
  });

  it("enters error when gradeCard fails with a code other than sitting_expired", async () => {
    vi.mocked(gradeCard).mockRejectedValue(
      new SittingHttpError("empty_sitting", "No cards due", 409),
    );
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Front",
    });

    await useSittingStore.getState().submitGrade("good");
    await vi.advanceTimersByTimeAsync(0);

    expect(useSittingStore.getState().phase).toBe("error");
    expect(useSittingStore.getState().notice).toBeNull();
    expect(openSitting).not.toHaveBeenCalled();
  });

  it("re-reads currentCard after rejectCard and presents the next front with the back hidden", async () => {
    vi.mocked(rejectCard).mockResolvedValue(undefined);
    vi.mocked(currentCard).mockResolvedValue({
      sittingId,
      cardId: nextCardId,
      front: "Next after reject",
      sittingComplete: false,
      outstandingCount: 1,
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "First front",
      back: "Back text",
      isBackVisible: true,
      selectedGradeIndex: 2,
    });

    await useSittingStore.getState().rejectCurrentCard();
    await vi.advanceTimersByTimeAsync(0);

    expect(rejectCard).toHaveBeenCalledWith(sittingId, cardId);
    expect(currentCard).toHaveBeenCalledWith(sittingId);
    const state = useSittingStore.getState();
    expect(state.phase).toBe("presented");
    expect(state.cardId).toBe(nextCardId);
    expect(state.front).toBe("Next after reject");
    expect(state.isBackVisible).toBe(false);
    expect(state.back).toBeNull();
    expect(state.selectedGradeIndex).toBe(0);
    expect(state.outstandingCount).toBe(1);
  });

  it("pushes due from currentCard into dueStore after a successful rejection", async () => {
    const updatedDue: DuePartition = {
      total: 3,
      notYetSeen: 0,
      seenStillOwed: 2,
      ripeOutsideSitting: 1,
    };
    vi.mocked(rejectCard).mockResolvedValue(undefined);
    vi.mocked(currentCard).mockResolvedValue({
      sittingId,
      cardId: nextCardId,
      front: "Next",
      sittingComplete: false,
      outstandingCount: 2,
      due: updatedDue,
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Front",
    });
    useDueStore.setState({ partition: DUE_PARTITION, isStale: true });

    await useSittingStore.getState().rejectCurrentCard();
    await vi.advanceTimersByTimeAsync(0);

    expect(useDueStore.getState().partition).toEqual(updatedDue);
    expect(useDueStore.getState().isStale).toBe(false);
  });

  it("completes the sitting when currentCard reports sittingComplete after a rejection", async () => {
    vi.mocked(rejectCard).mockResolvedValue(undefined);
    vi.mocked(currentCard).mockResolvedValue({
      sittingId,
      cardId: null,
      front: null,
      sittingComplete: true,
      outstandingCount: 0,
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Last card",
    });

    await useSittingStore.getState().rejectCurrentCard();
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(state.phase).toBe("complete");
    expect(state.cardId).toBeNull();
    expect(state.front).toBeNull();
  });

  it("re-opens once with a notice when rejectCard returns sitting_expired instead of entering error", async () => {
    vi.mocked(rejectCard).mockRejectedValue(
      new SittingHttpError(SITTING_EXPIRED, "Sitting no longer offered", 409),
    );
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId: "00000000-0000-4000-8000-000000000002",
      cardId,
      front: "Fresh front",
      sittingComplete: false,
      outstandingCount: 1,
    });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Stale front",
    });

    await useSittingStore.getState().rejectCurrentCard();
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(state.phase).not.toBe("error");
    expect(state.error).toBeNull();
    expect(state.notice).toMatch(/expired/i);
    expect(openSitting).toHaveBeenCalledTimes(1);
    expect(state.front).toBe("Fresh front");
    expect(currentCard).not.toHaveBeenCalled();
  });
});
