import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteListItem } from "../src/api/notes";
import NoteListOverlay from "../src/screens/NoteListOverlay";
import { useAppStore } from "../src/store/index";
import { useNotesStore } from "../src/store/notes";

const DOWN_ARROW = "\x1B[B";
const UP_ARROW = "\x1B[A";
const ENTER = "\r";

async function pressKey(
  stdin: { write: (data: string) => void },
  key: string,
): Promise<void> {
  stdin.write(key);
  await new Promise((resolve) => setTimeout(resolve, 30));
}

vi.mock("../src/hooks/useNotesPolling", () => ({
  useNotesPolling: vi.fn(),
}));

const GENERATING: NoteListItem = {
  noteId: "00000000-0000-4000-8000-000000000001",
  topicLabel: "TCP handshakes",
  distillationStatus: "generating",
  cardCount: 0,
  lastUpdatedAt: "2026-09-06T12:00:00Z",
};

const READY_ZERO: NoteListItem = {
  noteId: "00000000-0000-4000-8000-000000000002",
  topicLabel: "DNS resolution",
  distillationStatus: "ready",
  cardCount: 0,
  lastUpdatedAt: "2026-09-06T11:00:00Z",
};

const READY_WITH_CARDS: NoteListItem = {
  noteId: "00000000-0000-4000-8000-000000000003",
  topicLabel: "BGP routing",
  distillationStatus: "ready",
  cardCount: 3,
  lastUpdatedAt: "2026-09-06T11:00:00Z",
};

const FAILED: NoteListItem = {
  noteId: "00000000-0000-4000-8000-000000000004",
  topicLabel: "OSPF areas",
  distillationStatus: "failed",
  cardCount: 0,
  lastUpdatedAt: "2026-09-06T11:00:00Z",
};

describe("NoteListOverlay", () => {
  beforeEach(() => {
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    useAppStore.setState({
      isNotesOverlayOpen: true,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a generating row's badge with its elapsed age", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-06T12:05:00Z"));
    useNotesStore.setState({
      items: [GENERATING],
      isLoading: false,
      error: null,
    });

    const { lastFrame } = render(<NoteListOverlay />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("← ESC to go back");
    expect(frame).toContain("TCP handshakes");
    expect(frame).toContain("Generating (5m ago)");
  });

  it("distinguishes a ready row with zero cards from one with cards", () => {
    useNotesStore.setState({
      items: [READY_ZERO, READY_WITH_CARDS],
      isLoading: false,
      error: null,
    });

    const { lastFrame } = render(<NoteListOverlay />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("DNS resolution");
    expect(frame).toContain("BGP routing");
    expect(frame).toContain("0 cards");
    expect(frame).toContain("3 cards");
    expect(frame.indexOf("DNS resolution")).toBeLessThan(
      frame.indexOf("0 cards"),
    );
    expect(frame.indexOf("BGP routing")).toBeLessThan(frame.indexOf("3 cards"));
  });

  it('shows "Failed" for a failed note', () => {
    useNotesStore.setState({ items: [FAILED], isLoading: false, error: null });

    const { lastFrame } = render(<NoteListOverlay />);

    expect(lastFrame()).toContain("Failed");
  });

  it("renders an inline error above a still-visible prior list", () => {
    useNotesStore.setState({
      items: [READY_WITH_CARDS],
      isLoading: false,
      error: "network down",
    });

    const { lastFrame } = render(<NoteListOverlay />);
    const frame = lastFrame() ?? "";
    const errorIndex = frame.indexOf("network down");
    const topicIndex = frame.indexOf("BGP routing");

    expect(errorIndex).toBeGreaterThanOrEqual(0);
    expect(topicIndex).toBeGreaterThan(errorIndex);
  });

  it("shows a loading indicator only while items and isLoading are both empty", () => {
    useNotesStore.setState({ items: [], isLoading: true, error: null });
    const { lastFrame, rerender } = render(<NoteListOverlay />);
    expect(lastFrame()).toContain("Loading");

    useNotesStore.setState({
      items: [READY_WITH_CARDS],
      isLoading: true,
      error: null,
    });
    rerender(<NoteListOverlay />);
    expect(lastFrame()).not.toContain("Loading");
  });

  it("moves selectedIndex down and up within list bounds", async () => {
    useNotesStore.setState({
      items: [READY_ZERO, READY_WITH_CARDS, FAILED],
      isLoading: false,
      error: null,
    });

    const { stdin } = render(<NoteListOverlay />);

    await pressKey(stdin, DOWN_ARROW);
    expect(useAppStore.getState().selectedIndex).toBe(1);

    await pressKey(stdin, DOWN_ARROW);
    expect(useAppStore.getState().selectedIndex).toBe(2);

    await pressKey(stdin, DOWN_ARROW);
    expect(useAppStore.getState().selectedIndex).toBe(2);

    await pressKey(stdin, UP_ARROW);
    expect(useAppStore.getState().selectedIndex).toBe(1);
  });

  it("ignores arrow keys when the list is empty", async () => {
    const { stdin } = render(<NoteListOverlay />);

    await pressKey(stdin, DOWN_ARROW);
    await pressKey(stdin, UP_ARROW);

    expect(useAppStore.getState().selectedIndex).toBe(0);
  });

  it("opens detail when Enter is pressed on a ready note", async () => {
    useNotesStore.setState({
      items: [READY_ZERO],
      isLoading: false,
      error: null,
    });

    const { stdin } = render(<NoteListOverlay />);

    await pressKey(stdin, ENTER);

    expect(useAppStore.getState().isDetailOpen).toBe(true);
    expect(useAppStore.getState().selectedNoteId).toBe(READY_ZERO.noteId);
  });

  it("does not open detail when Enter is pressed on a generating or failed note", async () => {
    useNotesStore.setState({
      items: [GENERATING],
      isLoading: false,
      error: null,
    });

    const { stdin: stdinGenerating } = render(<NoteListOverlay />);
    await pressKey(stdinGenerating, ENTER);
    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useAppStore.getState().selectedNoteId).toBeNull();

    useAppStore.setState({
      isNotesOverlayOpen: true,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
    });
    useNotesStore.setState({
      items: [FAILED],
      isLoading: false,
      error: null,
    });

    const { stdin: stdinFailed } = render(<NoteListOverlay />);
    await pressKey(stdinFailed, ENTER);
    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useAppStore.getState().selectedNoteId).toBeNull();
  });
});
