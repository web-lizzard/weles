import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { gradeCard, SittingHttpError } from "../src/api/sittings";
import { SIGN_IN_EXPIRED_DETAIL, SIGN_IN_REQUIRED } from "../src/auth/expiry";
import { useSittingStore } from "../src/store/sitting";

vi.mock("../src/api/sittings", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/sittings")>();
  return {
    ...actual,
    gradeCard: vi.fn(),
  };
});

const sittingId = "00000000-0000-4000-8000-000000000001";
const cardId = "00000000-0000-4000-8000-000000000101";
const nextCardId = "00000000-0000-4000-8000-000000000102";

describe("sitting sign-in expiry", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useSittingStore.getState().reset();
    vi.mocked(gradeCard).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("enters error with expiry detail and keeps the current card on sign_in_required", async () => {
    vi.mocked(gradeCard).mockRejectedValue(
      new SittingHttpError(SIGN_IN_REQUIRED, "Sign-in required", 401),
    );
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "What is a SYN?",
      back: "Synchronize sequence numbers",
      isBackVisible: true,
      selectedGradeIndex: 2,
    });

    await useSittingStore.getState().submitGrade("good");
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(state.phase).toBe("error");
    expect(state.error).toEqual({
      code: SIGN_IN_REQUIRED,
      detail: SIGN_IN_EXPIRED_DETAIL,
    });
    expect(state.sittingId).toBe(sittingId);
    expect(state.cardId).toBe(cardId);
    expect(state.front).toBe("What is a SYN?");
    expect(state.back).toBe("Synchronize sequence numbers");
    expect(state.lastAction).toEqual({ type: "grade", grade: "good" });
  });

  it("retry after sign-in expiry records the grade and presents the next card", async () => {
    vi.mocked(gradeCard)
      .mockRejectedValueOnce(
        new SittingHttpError(SIGN_IN_REQUIRED, "Sign-in required", 401),
      )
      .mockResolvedValueOnce({
        sittingId,
        outstandingCount: 0,
        sittingComplete: false,
        nextCardId,
        nextFront: "Next front",
      });
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "What is a SYN?",
      back: "Back",
      isBackVisible: true,
    });

    await useSittingStore.getState().submitGrade("hard");
    await vi.advanceTimersByTimeAsync(0);
    expect(useSittingStore.getState().phase).toBe("error");

    await useSittingStore.getState().retry();
    await vi.advanceTimersByTimeAsync(0);

    const state = useSittingStore.getState();
    expect(gradeCard).toHaveBeenCalledTimes(2);
    expect(gradeCard).toHaveBeenLastCalledWith(sittingId, cardId, "hard");
    expect(state.phase).toBe("presented");
    expect(state.cardId).toBe(nextCardId);
    expect(state.front).toBe("Next front");
    expect(state.error).toBeNull();
  });
});
