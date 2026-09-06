import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteListItem } from "../src/api/notes";
import NoteListOverlay from "../src/screens/NoteListOverlay";
import { useNotesStore } from "../src/store/notes";

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
    const lines = (lastFrame() ?? "").split("\n");
    const zeroLine = lines.find((line) => line.includes("DNS resolution"));
    const withCardsLine = lines.find((line) => line.includes("BGP routing"));

    expect(zeroLine).toMatch(/\b0\b/);
    expect(withCardsLine).toMatch(/\b3\b/);
    expect(zeroLine).not.toContain("3");
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
});
