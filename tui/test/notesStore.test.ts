import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteListItem } from "../src/api/notes";
import { listNotes } from "../src/api/notes";
import { useNotesStore } from "../src/store/notes";

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

describe("useNotesStore", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    vi.mocked(listNotes).mockReset();
  });

  afterEach(() => {
    useNotesStore.getState().stopPolling();
    vi.useRealTimers();
  });

  it("fetches immediately on startPolling, then once per interval tick", async () => {
    vi.mocked(listNotes).mockResolvedValue([NOTE]);

    useNotesStore.getState().startPolling(1000);
    await vi.advanceTimersByTimeAsync(0);
    expect(listNotes).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1000);
    expect(listNotes).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(1000);
    expect(listNotes).toHaveBeenCalledTimes(3);
  });

  it("stops further fetches after stopPolling", async () => {
    vi.mocked(listNotes).mockResolvedValue([NOTE]);

    useNotesStore.getState().startPolling(1000);
    await vi.advanceTimersByTimeAsync(0);
    useNotesStore.getState().stopPolling();

    await vi.advanceTimersByTimeAsync(5000);
    expect(listNotes).toHaveBeenCalledTimes(1);
  });

  it("sets error and leaves prior items untouched when a fetch fails", async () => {
    useNotesStore.setState({ items: [NOTE], isLoading: false, error: null });
    vi.mocked(listNotes).mockRejectedValue(new Error("network down"));

    await useNotesStore.getState().fetchNotes();

    expect(useNotesStore.getState().error).toBe("network down");
    expect(useNotesStore.getState().items).toEqual([NOTE]);
  });

  it("clears a prior error and updates items on the next successful tick", async () => {
    vi.mocked(listNotes)
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce([NOTE]);

    useNotesStore.getState().startPolling(1000);
    await vi.advanceTimersByTimeAsync(0);
    expect(useNotesStore.getState().error).toBe("network down");

    await vi.advanceTimersByTimeAsync(1000);
    expect(useNotesStore.getState().error).toBeNull();
    expect(useNotesStore.getState().items).toEqual([NOTE]);
  });
});
