import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  gradeCard,
  openSitting,
  revealBack,
  SITTING_EXPIRED,
  SittingHttpError,
} from "../src/api/sittings";
import SittingOverlay from "../src/screens/SittingOverlay";
import { useAppStore } from "../src/store/index";
import { useSittingStore } from "../src/store/sitting";

const DOWN_ARROW = "\x1B[B";
const ENTER = "\r";
const ESC = "\x1B";

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
    rejectCard: vi.fn(),
    currentCard: vi.fn(),
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
    isResumed: false,
    outstandingCount: 0,
    notice: null,
  });
}

describe("SittingOverlay", () => {
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

  it("calls openSitting on mount and shows a loading indicator until the card front appears", async () => {
    let resolveOpen!: (value: Awaited<ReturnType<typeof openSitting>>) => void;
    vi.mocked(openSitting).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveOpen = resolve;
        }),
    );

    const { lastFrame } = render(<SittingOverlay />);

    expect(openSitting).toHaveBeenCalledTimes(1);
    expect(lastFrame()).toContain("Loading");

    resolveOpen({
      kind: "opened",
      sittingId,
      cardId,
      front: "What is a SYN?",
      sittingComplete: false,
      outstandingCount: 0,
    });
    await vi.advanceTimersByTimeAsync(0);

    const frame = lastFrame() ?? "";
    expect(frame).toContain("What is a SYN?");
    expect(frame).toContain("← ESC to go back");
    expect(frame).toContain("Front");
    expect(frame).toContain("Press t to toggle card");
  });

  it("closes the overlay and resets the store when ESC is pressed", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "Front line",
      sittingComplete: false,
      outstandingCount: 0,
    });

    const { stdin } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, ESC);
    await vi.advanceTimersByTimeAsync(0);

    expect(useAppStore.getState().isSittingOverlayOpen).toBe(false);
    expect(useSittingStore.getState().sittingId).toBeNull();
  });

  it("shows the card back after t is pressed and hides it when t is pressed again", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "Front line",
      sittingComplete: false,
      outstandingCount: 0,
    });
    vi.mocked(revealBack).mockResolvedValue({
      sittingId,
      cardId,
      front: "Front line",
      back: "Back line",
    });

    const { stdin, lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, "t");
    await vi.advanceTimersByTimeAsync(0);
    expect(revealBack).toHaveBeenCalledWith(sittingId, cardId);
    expect(lastFrame()).toContain("Back line");

    await pressKey(stdin, "t");
    expect(lastFrame()).not.toContain("Back line");
    expect(lastFrame()).toContain("Front line");
  });

  it("submits good when 3 is pressed while only the front is visible", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "Front line",
      sittingComplete: false,
      outstandingCount: 0,
    });
    vi.mocked(gradeCard).mockResolvedValue({
      sittingId,
      outstandingCount: 0,
      sittingComplete: true,
      nextCardId: null,
      nextFront: null,
    });

    const { stdin } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, "3");
    await vi.advanceTimersByTimeAsync(0);

    expect(gradeCard).toHaveBeenCalledWith(sittingId, cardId, "good");
  });

  it("still submits a grade when the back is showing", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "Front line",
      sittingComplete: false,
      outstandingCount: 0,
    });
    vi.mocked(revealBack).mockResolvedValue({
      sittingId,
      cardId,
      front: "Front line",
      back: "Back line",
    });
    vi.mocked(gradeCard).mockResolvedValue({
      sittingId,
      outstandingCount: 0,
      sittingComplete: true,
      nextCardId: null,
      nextFront: null,
    });

    const { stdin } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, "t");
    await vi.advanceTimersByTimeAsync(0);
    await pressKey(stdin, "2");
    await vi.advanceTimersByTimeAsync(0);

    expect(gradeCard).toHaveBeenCalledWith(sittingId, cardId, "hard");
  });

  it("moves the highlighted grade with arrows, submits on Enter, and shows the next card front", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "First front",
      sittingComplete: false,
      outstandingCount: 0,
    });
    vi.mocked(gradeCard).mockResolvedValue({
      sittingId,
      outstandingCount: 0,
      sittingComplete: false,
      nextCardId,
      nextFront: "Second front",
    });

    const { stdin, lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, DOWN_ARROW);
    await pressKey(stdin, DOWN_ARROW);
    await pressKey(stdin, ENTER);
    await vi.advanceTimersByTimeAsync(0);

    expect(gradeCard).toHaveBeenCalledWith(sittingId, cardId, "good");
    expect(lastFrame()).toContain("Second front");
  });

  it("shows a nothing-due message when opening finds no cards due for review", async () => {
    vi.mocked(openSitting).mockResolvedValue({ kind: "nothing_due" });

    const { lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    expect(lastFrame()).toMatch(/nothing due/i);
    expect(lastFrame()).not.toContain("nothing_due");
  });

  it("shows a completion message after the last card is graded", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "Last card",
      sittingComplete: false,
      outstandingCount: 0,
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

    expect(lastFrame()).toContain("Sitting complete");
  });

  it("shows the HTTP error detail and a retry hint when open fails", async () => {
    vi.mocked(openSitting).mockRejectedValue(
      new SittingHttpError("sitting_not_found", "Sitting was not found.", 404),
    );

    const { lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    expect(lastFrame()).toContain("Sitting was not found.");
    expect(lastFrame()).toMatch(/press r/i);
  });

  it("calls retry when r is pressed in the error phase", async () => {
    vi.mocked(openSitting)
      .mockRejectedValueOnce(
        new SittingHttpError(
          "network_error",
          "Could not reach the server.",
          503,
        ),
      )
      .mockResolvedValueOnce({
        kind: "opened",
        sittingId,
        cardId,
        front: "Recovered front",
        sittingComplete: false,
        outstandingCount: 0,
      });

    const { stdin, lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);
    expect(lastFrame()).toContain("Could not reach the server.");

    await pressKey(stdin, "r");
    await vi.advanceTimersByTimeAsync(0);

    expect(openSitting).toHaveBeenCalledTimes(2);
    expect(lastFrame()).toContain("Recovered front");
  });

  it("shows a Resumed marker and the outstanding count when open returns a resumed sitting", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "resumed",
      sittingId,
      cardId,
      front: "Pick up here",
      sittingComplete: false,
      outstandingCount: 3,
    });

    const { lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    const frame = lastFrame() ?? "";
    expect(frame).toContain("Resumed");
    expect(frame).toContain("Pick up here");
    expect(frame).toMatch(/3 left/i);
  });

  it("shows the outstanding count without a Resumed marker on a freshly opened sitting", async () => {
    vi.mocked(openSitting).mockResolvedValue({
      kind: "opened",
      sittingId,
      cardId,
      front: "New session front",
      sittingComplete: false,
      outstandingCount: 2,
    });

    const { lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    const frame = lastFrame() ?? "";
    expect(frame).not.toContain("Resumed");
    expect(frame).toContain("New session front");
    expect(frame).toMatch(/2 left/i);
  });

  it("shows an expiry notice alongside the card instead of replacing it", async () => {
    vi.mocked(openSitting)
      .mockResolvedValueOnce({
        kind: "opened",
        sittingId,
        cardId,
        front: "Before expiry",
        sittingComplete: false,
        outstandingCount: 1,
      })
      .mockResolvedValueOnce({
        kind: "opened",
        sittingId: "00000000-0000-4000-8000-000000000002",
        cardId,
        front: "After recovery",
        sittingComplete: false,
        outstandingCount: 1,
      });
    vi.mocked(gradeCard).mockRejectedValue(
      new SittingHttpError(SITTING_EXPIRED, "Sitting no longer offered", 409),
    );

    const { stdin, lastFrame } = render(<SittingOverlay />);
    await vi.advanceTimersByTimeAsync(0);

    await pressKey(stdin, "3");
    await vi.advanceTimersByTimeAsync(0);

    const frame = lastFrame() ?? "";
    expect(frame).toMatch(/expired/i);
    expect(frame).toContain("After recovery");
    expect(frame).not.toMatch(/press r/i);
  });
});
