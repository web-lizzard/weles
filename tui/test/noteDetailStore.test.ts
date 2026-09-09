import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteDetail } from "../src/api/notes";
import { getNote } from "../src/api/notes";
import { useAppStore } from "../src/store/index";
import { useNoteDetailStore } from "../src/store/noteDetail";
import { useNotesStore } from "../src/store/notes";

vi.mock("../src/api/notes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/notes")>();
  return {
    ...actual,
    getNote: vi.fn(),
  };
});

const NOTE_DETAIL: NoteDetail = {
  noteId: "00000000-0000-4000-8000-000000000001",
  topic: {
    id: "00000000-0000-4000-8000-000000000010",
    label: "TCP handshakes",
  },
  content: "Full note content",
  blocks: [],
  tags: [
    {
      id: "00000000-0000-4000-8000-000000000020",
      label: "networking",
    },
  ],
  distillationStatus: "ready",
  approvedAt: "2026-09-06T12:00:00Z",
  createdAt: "2026-09-06T12:00:00Z",
  updatedAt: "2026-09-06T12:00:00Z",
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("useNoteDetailStore", () => {
  beforeEach(() => {
    useNoteDetailStore.setState({ note: null, isLoading: false });
    useAppStore.setState({
      isNotesOverlayOpen: false,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
    });
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    vi.mocked(getNote).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sets note on a successful fetchNote", async () => {
    vi.mocked(getNote).mockResolvedValue(NOTE_DETAIL);

    await useNoteDetailStore.getState().fetchNote(NOTE_DETAIL.noteId);

    expect(useNoteDetailStore.getState().note).toEqual(NOTE_DETAIL);
    expect(useNoteDetailStore.getState().isLoading).toBe(false);
  });

  it("closes the detail view and surfaces list error when fetchNote fails", async () => {
    useAppStore.setState({
      isDetailOpen: true,
      selectedNoteId: NOTE_DETAIL.noteId,
    });
    vi.mocked(getNote).mockRejectedValue(new Error("Note not found"));

    await useNoteDetailStore.getState().fetchNote(NOTE_DETAIL.noteId);

    expect(useNoteDetailStore.getState().isLoading).toBe(false);
    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useNotesStore.getState().error).toBe("Note not found");
  });

  it("clears the previous note before a new response lands", async () => {
    const secondNote: NoteDetail = {
      ...NOTE_DETAIL,
      noteId: "00000000-0000-4000-8000-000000000002",
      content: "Updated content",
    };

    useNoteDetailStore.setState({ note: NOTE_DETAIL, isLoading: false });

    const pending = deferred<NoteDetail>();
    vi.mocked(getNote).mockReturnValue(pending.promise);

    const fetchPromise = useNoteDetailStore
      .getState()
      .fetchNote(secondNote.noteId);

    expect(useNoteDetailStore.getState().note).toBeNull();
    expect(useNoteDetailStore.getState().isLoading).toBe(true);

    pending.resolve(secondNote);
    await fetchPromise;

    expect(useNoteDetailStore.getState().note).toEqual(secondNote);
    expect(useNoteDetailStore.getState().isLoading).toBe(false);
  });
});
