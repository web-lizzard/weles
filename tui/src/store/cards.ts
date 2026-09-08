import { create } from "zustand";
import { type Card, listCards } from "../api/cards.js";
import { useAppStore } from "./index.js";
import { useNotesStore } from "./notes.js";

type CardsState = {
  cards: Card[];
  isLoading: boolean;
};

type CardsActions = {
  fetchCards: (noteId: string) => Promise<void>;
  refresh: () => Promise<void>;
};

function surfaceCardsError(error: unknown) {
  useAppStore.getState().closeDetail();
  useNotesStore.setState({
    error: error instanceof Error ? error.message : String(error),
  });
}

export const useCardsStore = create<CardsState & CardsActions>((set) => ({
  cards: [],
  isLoading: false,
  fetchCards: async (noteId: string) => {
    set({ cards: [], isLoading: true });
    try {
      const cards = await listCards(noteId);
      set({ cards, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      surfaceCardsError(error);
    }
  },
  refresh: async () => {
    const noteId = useAppStore.getState().selectedNoteId;
    if (noteId === null) return;
    try {
      const cards = await listCards(noteId);
      set({ cards, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      surfaceCardsError(error);
    }
  },
}));
