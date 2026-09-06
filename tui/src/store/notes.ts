import { create } from "zustand";
import { listNotes, type NoteListItem } from "../api/notes.js";

type NotesState = {
  items: NoteListItem[];
  isLoading: boolean;
  error: string | null;
};

type NotesActions = {
  fetchNotes: () => Promise<void>;
  startPolling: (intervalMs: number) => void;
  stopPolling: () => void;
};

let pollIntervalId: ReturnType<typeof setInterval> | null = null;

export const useNotesStore = create<NotesState & NotesActions>((set, get) => ({
  items: [],
  isLoading: false,
  error: null,
  fetchNotes: async () => {
    set({ isLoading: true });
    try {
      const items = await listNotes();
      set({ items, error: null });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : String(error) });
    } finally {
      set({ isLoading: false });
    }
  },
  startPolling: (intervalMs: number) => {
    get().stopPolling();
    void get().fetchNotes();
    pollIntervalId = setInterval(() => {
      void get().fetchNotes();
    }, intervalMs);
  },
  stopPolling: () => {
    if (pollIntervalId !== null) {
      clearInterval(pollIntervalId);
      pollIntervalId = null;
    }
  },
}));
