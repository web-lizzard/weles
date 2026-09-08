import { create } from "zustand";

export type NoteTab = "note" | "cards";

type AppState = {
  isNotesOverlayOpen: boolean;
  selectedIndex: number;
  isDetailOpen: boolean;
  selectedNoteId: string | null;
  activeNoteTab: NoteTab;
  selectedCardId: string | null;
};

type AppActions = {
  openNotes: () => void;
  closeNotes: () => void;
  setSelectedIndex: (index: number) => void;
  openDetail: (noteId: string) => void;
  closeDetail: () => void;
  setActiveNoteTab: (tab: NoteTab) => void;
  openCard: (cardId: string) => void;
  closeCard: () => void;
};

const clearedNoteView = {
  activeNoteTab: "note" as const,
  selectedCardId: null,
};

export const useAppStore = create<AppState & AppActions>((set) => ({
  isNotesOverlayOpen: false,
  selectedIndex: 0,
  isDetailOpen: false,
  selectedNoteId: null,
  ...clearedNoteView,
  openNotes: () => set({ isNotesOverlayOpen: true }),
  closeNotes: () =>
    set({
      isNotesOverlayOpen: false,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
      ...clearedNoteView,
    }),
  setSelectedIndex: (index) => set({ selectedIndex: index }),
  openDetail: (noteId) =>
    set({
      isDetailOpen: true,
      selectedNoteId: noteId,
      ...clearedNoteView,
    }),
  closeDetail: () =>
    set({
      isDetailOpen: false,
      selectedNoteId: null,
      ...clearedNoteView,
    }),
  setActiveNoteTab: (tab) => set({ activeNoteTab: tab }),
  openCard: (cardId) => set({ selectedCardId: cardId }),
  closeCard: () => set({ selectedCardId: null }),
}));
