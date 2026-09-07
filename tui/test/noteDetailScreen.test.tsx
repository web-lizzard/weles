import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

  it("renders the back hint, topic, joined tags, and full content when loaded", () => {
    useAppStore.setState({ selectedNoteId: NOTE_ID });
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

    useAppStore.setState({ selectedNoteId: NOTE_ID });
    useNoteDetailStore.setState({ note: noteWithoutTags, isLoading: false });

    const { lastFrame } = render(<NoteDetailScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("TCP handshakes");
    expect(frame).toContain("Full note content for the detail view");
    expect(frame).not.toContain("Tags:");
    expect(frame).not.toContain(" · ");
  });
});
