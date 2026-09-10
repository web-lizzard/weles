import { create } from "zustand";
import type { AnchorLocation } from "../api/cards.js";

export type NoteTab = "note" | "cards";

type AppState = {
  isNotesOverlayOpen: boolean;
  isSittingOverlayOpen: boolean;
  selectedIndex: number;
  isDetailOpen: boolean;
  selectedNoteId: string | null;
  activeNoteTab: NoteTab;
  selectedCardId: string | null;
  highlightedAnchor: { cardId: string; location: AnchorLocation | null } | null;
};

type AppActions = {
  openNotes: () => void;
  closeNotes: () => void;
  openSittingOverlay: () => void;
  closeSittingOverlay: () => void;
  setSelectedIndex: (index: number) => void;
  openDetail: (noteId: string) => void;
  closeDetail: () => void;
  setActiveNoteTab: (tab: NoteTab) => void;
  openCard: (cardId: string) => void;
  closeCard: () => void;
  jumpToAnchor: (cardId: string, location: AnchorLocation | null) => void;
};

const clearedNoteView = {
  activeNoteTab: "note" as const,
  selectedCardId: null,
  highlightedAnchor: null,
};

export const useAppStore = create<AppState & AppActions>((set) => ({
  isNotesOverlayOpen: false,
  isSittingOverlayOpen: false,
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
  openSittingOverlay: () => set({ isSittingOverlayOpen: true }),
  closeSittingOverlay: () => set({ isSittingOverlayOpen: false }),
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
  setActiveNoteTab: (tab) =>
    set({ activeNoteTab: tab, highlightedAnchor: null }),
  openCard: (cardId) => set({ selectedCardId: cardId }),
  closeCard: () => set({ selectedCardId: null }),
  jumpToAnchor: (cardId, location) =>
    set({
      activeNoteTab: "note",
      selectedCardId: null,
      highlightedAnchor: { cardId, location },
    }),
}));
