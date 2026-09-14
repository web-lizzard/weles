import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AnchorLocation } from "../src/api/cards";
import type { NoteDetail } from "../src/api/notes";
import { getNote } from "../src/api/notes";
import NoteDetailScreen from "../src/screens/NoteDetailScreen";
import { useAppStore } from "../src/store/index";
import { useNoteDetailStore } from "../src/store/noteDetail";

vi.mock("../src/api/notes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/notes")>();
  return {
    ...actual,
    getNote: vi.fn(),
  };
});

const NOTE_ID = "00000000-0000-4000-8000-000000000001";

const NOTE_DETAIL: NoteDetail = {
  noteId: NOTE_ID,
  topic: {
    id: "00000000-0000-4000-8000-000000000010",
    label: "TCP handshakes",
  },
  content: "Full note content for the detail view",
  blocks: [{ index: 0, text: "Full note content for the detail view" }],
  tags: [
    {
      id: "00000000-0000-4000-8000-000000000020",
      label: "networking",
    },
    {
      id: "00000000-0000-4000-8000-000000000021",
      label: "protocols",
    },
  ],
  distillationStatus: "ready",
  approvedAt: "2026-09-06T12:00:00Z",
  createdAt: "2026-09-06T12:00:00Z",
  updatedAt: "2026-09-06T12:00:00Z",
};

async function waitFor(
  predicate: () => boolean,
  timeoutMs = 2000,
  intervalMs = 20,
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (predicate()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("Timed out waiting for condition");
}

const HIDDEN_INTRO = "Hidden intro about UDP.";
const ANCHORED_BLOCK = "The handshake begins here.";
const QUOTED_RUN = "handshake begins";
const INVERSE = "\u001b[7m";
const INVERSE_OFF = "\u001b[27m";

const BLOCKS_NOTE: NoteDetail = {
  ...NOTE_DETAIL,
  content: `${HIDDEN_INTRO}\n\n${ANCHORED_BLOCK}`,
  blocks: [
    { index: 0, text: HIDDEN_INTRO },
    { index: 1, text: ANCHORED_BLOCK },
  ],
};

const EXACT_LOCATION: AnchorLocation = {
  blockIndex: 1,
  start: 4,
  end: 20,
  precision: "exact",
};

const BLOCK_LOCATION: AnchorLocation = {
  blockIndex: 1,
  start: 0,
  end: ANCHORED_BLOCK.length,
  precision: "block",
};

const CARD_ID = "00000000-0000-4000-8000-000000000101";

describe("NoteDetailScreen", () => {
  beforeEach(() => {
    useAppStore.setState({
      isNotesOverlayOpen: true,
      selectedIndex: 0,
      isDetailOpen: true,
      selectedNoteId: null,
    });
    useNoteDetailStore.setState({ note: null, isLoading: false });
    vi.mocked(getNote).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads the selected note when mounted with a selectedNoteId", async () => {
    useAppStore.setState({ selectedNoteId: NOTE_ID });
    vi.mocked(getNote).mockResolvedValue(NOTE_DETAIL);

    render(<NoteDetailScreen />);

    await waitFor(() => vi.mocked(getNote).mock.calls.length > 0);
    expect(getNote).toHaveBeenCalledWith(NOTE_ID);
  });

  // R1-F2: plan Contract (Phase 10) fetches unconditionally whenever
  // selectedNoteId is non-null; skip guard is undocumented drift.
  it("refetches when mounted with a selectedNoteId that already matches a cached note", async () => {
    useAppStore.setState({ selectedNoteId: NOTE_ID });
    useNoteDetailStore.setState({ note: NOTE_DETAIL, isLoading: false });
    vi.mocked(getNote).mockResolvedValue(NOTE_DETAIL);

    render(<NoteDetailScreen />);

    await waitFor(() => vi.mocked(getNote).mock.calls.length > 0);
    expect(getNote).toHaveBeenCalledWith(NOTE_ID);
  });

  it("renders the back hint, topic, joined tags, and full content when loaded", () => {
    useNoteDetailStore.setState({ note: NOTE_DETAIL, isLoading: false });

    const { lastFrame } = render(<NoteDetailScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("← ESC to go back");
    expect(frame).toContain("TCP handshakes");
    expect(frame).toContain("Tags:");
    expect(frame).toContain("networking · protocols");
    expect(frame).toContain("Full note content for the detail view");
  });

  it("shows a loading indicator only while the note is still null", () => {
    useAppStore.setState({ selectedNoteId: NOTE_ID });
    useNoteDetailStore.setState({ note: null, isLoading: true });

    const { lastFrame, rerender } = render(<NoteDetailScreen />);
    expect(lastFrame()).toContain("Loading...");

    useNoteDetailStore.setState({ note: NOTE_DETAIL, isLoading: false });
    rerender(<NoteDetailScreen />);
    expect(lastFrame()).not.toContain("Loading...");
  });

  it("omits tag separators when the note has no tags", () => {
    const noteWithoutTags: NoteDetail = {
      ...NOTE_DETAIL,
      tags: [],
    };

    useNoteDetailStore.setState({ note: noteWithoutTags, isLoading: false });

    const { lastFrame } = render(<NoteDetailScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("TCP handshakes");
    expect(frame).toContain("Full note content for the detail view");
    expect(frame).not.toContain("Tags:");
    expect(frame).not.toContain(" · ");
  });

  it("marks the quoted run of an exact location and scrolls it to the first visible line", () => {
    useNoteDetailStore.setState({ note: BLOCKS_NOTE, isLoading: false });
    useAppStore.setState({
      highlightedAnchor: { cardId: CARD_ID, location: EXACT_LOCATION },
    });

    const frame = render(<NoteDetailScreen />).lastFrame() ?? "";
    const lines = frame.split("\n");
    // Phase 14 Contract: "An anchor opens NoteDetailScreen scrolled so that
    // the anchored block is the first visible line" — the note body renders
    // inside a SourceViewport, so a non-zero offset surfaces a "more above"
    // marker immediately before the anchored block's line.
    const moreAboveIndex = lines.findIndex((line) => /more above/i.test(line));

    expect(frame).not.toContain(HIDDEN_INTRO);
    expect(moreAboveIndex).toBeGreaterThanOrEqual(0);
    expect(lines[moreAboveIndex + 1]).toContain(
      `The ${INVERSE}${QUOTED_RUN}${INVERSE_OFF} here.`,
    );
    expect(frame).not.toContain(`${INVERSE}${ANCHORED_BLOCK}${INVERSE_OFF}`);
  });

  it("marks the whole anchored block when precision is block and scrolls it to the first visible line", () => {
    useNoteDetailStore.setState({ note: BLOCKS_NOTE, isLoading: false });
    useAppStore.setState({
      highlightedAnchor: { cardId: CARD_ID, location: BLOCK_LOCATION },
    });

    const frame = render(<NoteDetailScreen />).lastFrame() ?? "";
    const lines = frame.split("\n");
    const moreAboveIndex = lines.findIndex((line) => /more above/i.test(line));

    expect(frame).not.toContain(HIDDEN_INTRO);
    expect(moreAboveIndex).toBeGreaterThanOrEqual(0);
    expect(lines[moreAboveIndex + 1]).toContain(
      `${INVERSE}${ANCHORED_BLOCK}${INVERSE_OFF}`,
    );
  });

  it("renders from the top with a notice when the highlighted location is missing", () => {
    useNoteDetailStore.setState({ note: BLOCKS_NOTE, isLoading: false });
    useAppStore.setState({
      highlightedAnchor: { cardId: CARD_ID, location: null },
    });

    const frame = render(<NoteDetailScreen />).lastFrame() ?? "";

    expect(frame).toMatch(/not found/i);
    expect(frame).toContain(HIDDEN_INTRO);
    expect(frame).toContain(ANCHORED_BLOCK);
  });
});
