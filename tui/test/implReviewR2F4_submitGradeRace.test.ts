import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { gradeCard, openSitting, revealBack } from "../src/api/sittings";
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

describe("submitGrade re-entrancy", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useSittingStore.setState({
      phase: "presented",
      sittingId,
      cardId,
      front: "Front",
      back: null,
      isBackVisible: false,
      selectedGradeIndex: 0,
      isSubmitting: false,
      error: null,
      lastAction: null,
    });
    vi.mocked(openSitting).mockReset();
    vi.mocked(revealBack).mockReset();
    vi.mocked(gradeCard).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not issue a second gradeCard call when submitGrade is invoked again before the first resolves", async () => {
    let resolveFirst!: (value: {
      sittingId: string;
      outstandingCount: number;
      sittingComplete: boolean;
      nextCardId: string | null;
      nextFront: string | null;
    }) => void;
    const first = new Promise((resolve) => {
      resolveFirst = resolve;
    });
    vi.mocked(gradeCard).mockReturnValue(first as ReturnType<typeof gradeCard>);

    const p1 = useSittingStore.getState().submitGrade("good");
    const p2 = useSittingStore.getState().submitGrade("hard");

    resolveFirst({
      sittingId,
      outstandingCount: 0,
      sittingComplete: true,
      nextCardId: null,
      nextFront: null,
    });
    await Promise.all([p1, p2]);
    await vi.advanceTimersByTimeAsync(0);

    expect(gradeCard).toHaveBeenCalledTimes(1);
  });
});
