import { create } from "zustand";

type AppState = {
  isNotesOverlayOpen: boolean;
};

type AppActions = {
  openNotes: () => void;
  closeNotes: () => void;
};

export const useAppStore = create<AppState & AppActions>((set) => ({
  isNotesOverlayOpen: false,
  openNotes: () => set({ isNotesOverlayOpen: true }),
  closeNotes: () => set({ isNotesOverlayOpen: false }),
}));
