import { create } from "zustand";
import { getNote, type NoteDetail } from "../api/notes.js";
import { useAppStore } from "./index.js";
import { useNotesStore } from "./notes.js";

type NoteDetailState = {
  note: NoteDetail | null;
  isLoading: boolean;
};

type NoteDetailActions = {
  fetchNote: (noteId: string) => Promise<void>;
};

export const useNoteDetailStore = create<NoteDetailState & NoteDetailActions>(
  (set) => ({
    note: null,
    isLoading: false,
    fetchNote: async (noteId: string) => {
      set({ note: null, isLoading: true });
      try {
        const note = await getNote(noteId);
        set({ note, isLoading: false });
      } catch (error) {
        set({ isLoading: false });
        useAppStore.getState().closeDetail();
        useNotesStore.setState({
          error: error instanceof Error ? error.message : String(error),
        });
      }
    },
  }),
);
