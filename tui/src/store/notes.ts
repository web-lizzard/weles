import { create } from "zustand";
import type { NoteListItem } from "../api/notes.js";

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

export const useNotesStore = create<NotesState & NotesActions>(() => ({
  items: [],
  isLoading: false,
  error: null,
  fetchNotes: async () => {
    throw new Error("Not implemented");
  },
  startPolling: (intervalMs: number) => {
    throw new Error("Not implemented");
  },
  stopPolling: () => {
    throw new Error("Not implemented");
  },
}));
