import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteListItem } from "../src/api/notes";
import { listNotes } from "../src/api/notes";
import { useNotesStore } from "../src/store/notes";

// R1-F6
vi.mock("../src/api/notes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/notes")>();
  return {
    ...actual,
    listNotes: vi.fn(),
  };
});

const NOTE: NoteListItem = {
  noteId: "00000000-0000-4000-8000-000000000001",
  topicLabel: "TCP handshakes",
  distillationStatus: "ready",
  cardCount: 3,
  lastUpdatedAt: "2026-09-06T12:00:00Z",
};

describe("useNotesStore polling lifecycle — overlapping start calls (R1-F6)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    vi.mocked(listNotes).mockReset();
  });

  afterEach(() => {
    useNotesStore.getState().stopPolling();
    vi.useRealTimers();
  });

  it("stopPolling clears every interval started, not only the most recent one", async () => {
    vi.mocked(listNotes).mockResolvedValue([NOTE]);

    useNotesStore.getState().startPolling(1000);
    await vi.advanceTimersByTimeAsync(0);
    useNotesStore.getState().startPolling(1000);
    await vi.advanceTimersByTimeAsync(0);
    expect(listNotes).toHaveBeenCalledTimes(2);

    useNotesStore.getState().stopPolling();
    await vi.advanceTimersByTimeAsync(5000);

    expect(listNotes).toHaveBeenCalledTimes(2);
  });
});
