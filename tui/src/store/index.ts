import { create } from "zustand";

type AppState = {
  isNotesOverlayOpen: boolean;
};

type AppActions = {
  openNotes: () => void;
  closeNotes: () => void;
};

export const useAppStore = create<AppState & AppActions>(() => ({
  isNotesOverlayOpen: false,
  openNotes: () => {},
  closeNotes: () => {},
}));
