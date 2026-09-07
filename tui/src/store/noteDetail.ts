import { create } from "zustand";
import type { NoteDetail } from "../api/notes.js";

type NoteDetailState = {
  note: NoteDetail | null;
  isLoading: boolean;
};

type NoteDetailActions = {
  fetchNote: (noteId: string) => Promise<void>;
};

export const useNoteDetailStore = create<NoteDetailState & NoteDetailActions>(
  () => ({
    note: null,
    isLoading: false,
    fetchNote: async (_noteId: string) => {
      throw new Error("Not implemented");
    },
  }),
);
