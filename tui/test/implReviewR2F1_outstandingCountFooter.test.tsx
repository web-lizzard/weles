import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  gradeCard,
  openSitting,
  revealBack,
  SittingHttpError,
} from "../src/api/sittings";
import SittingOverlay from "../src/screens/SittingOverlay";
import { useAppStore } from "../src/store/index";
import { useSittingStore } from "../src/store/sitting";

async function pressKey(
  stdin: { write: (data: string) => void },
  key: string,
): Promise<void> {
  stdin.write(key);
  await vi.advanceTimersByTimeAsync(30);
}

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
    isResumed: false,
    outstandingCount: 0,
    notice: null,
  });
}

describe("SittingOverlay outstanding count (R2-F1)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useAppStore.setState({ isSittingOverlayOpen: true });
    resetStore();
    vi.mocked(openSitting).mockReset();
    vi.mocked(revealBack).mockReset();
    vi.mocked(gradeCard).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("still reports how many cards are left when a grade fails and the live sitting is shown as an error", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "What is a SYN?",
      sittingComplete: false,
      outstandingCount: 3,
    });
    vi.mocked(gradeCard).mockRejectedValue(
      new SittingHttpError(
        "card_not_presentable",
        "Not the card in front",
        409,
      ),
    );

    const { stdin, lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, "3");
    await vi.advanceTimersByTimeAsync(0);

    expect(useSittingStore.getState().sittingId).toBe(sittingId);
    expect(lastFrame() ?? "").toMatch(/3 left/i);
  });

  it("reports zero cards left once the sitting it still holds is complete", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "Last card",
      sittingComplete: false,
      outstandingCount: 1,
    });
    vi.mocked(gradeCard).mockResolvedValue({
      sittingId,
      outstandingCount: 0,
      sittingComplete: true,
      nextCardId: null,
      nextFront: null,
    });

    const { stdin, lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, "3");
    await vi.advanceTimersByTimeAsync(0);

    expect(useSittingStore.getState().sittingId).toBe(sittingId);
    expect(lastFrame() ?? "").toMatch(/0 left/i);
  });
});
