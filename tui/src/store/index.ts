import { create } from "zustand";

type AppState = {
  isNotesOverlayOpen: boolean;
  selectedIndex: number;
  isDetailOpen: boolean;
  selectedNoteId: string | null;
};

type AppActions = {
  openNotes: () => void;
  closeNotes: () => void;
  setSelectedIndex: (index: number) => void;
  openDetail: (noteId: string) => void;
  closeDetail: () => void;
};

export const useAppStore = create<AppState & AppActions>((set) => ({
  isNotesOverlayOpen: false,
  selectedIndex: 0,
  isDetailOpen: false,
  selectedNoteId: null,
  openNotes: () => set({ isNotesOverlayOpen: true }),
  closeNotes: () => set({ isNotesOverlayOpen: false }),
  setSelectedIndex: (_index) => {
    throw new Error("Not implemented");
  },
  openDetail: (_noteId) => {
    throw new Error("Not implemented");
  },
  closeDetail: () => {
    throw new Error("Not implemented");
  },
}));
