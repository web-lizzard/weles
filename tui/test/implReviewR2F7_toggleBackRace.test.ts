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
    rejectCard: vi.fn(),
    currentCard: vi.fn(),
  };
});

const sittingId = "00000000-0000-4000-8000-000000000001";
const cardId = "00000000-0000-4000-8000-000000000101";

describe("toggleBack re-entrancy on first reveal", () => {
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

  it("fetches the back at most once even when toggleBack is called twice before the first reveal resolves", async () => {
    let resolveReveal!: (value: {
      sittingId: string;
      cardId: string;
      front: string;
      back: string;
    }) => void;
    const pending = new Promise((resolve) => {
      resolveReveal = resolve;
    });
    vi.mocked(revealBack).mockReturnValue(
      pending as ReturnType<typeof revealBack>,
    );

    const p1 = useSittingStore.getState().toggleBack();
    const p2 = useSittingStore.getState().toggleBack();

    resolveReveal({ sittingId, cardId, front: "Front", back: "Back text" });
    await Promise.all([p1, p2]);
    await vi.advanceTimersByTimeAsync(0);

    expect(revealBack).toHaveBeenCalledTimes(1);
  });
});
