import { create } from "zustand";
import type { Card } from "../api/cards.js";

type CardsState = {
  cards: Card[];
  isLoading: boolean;
};

type CardsActions = {
  fetchCards: (noteId: string) => Promise<void>;
  refresh: () => Promise<void>;
};

export const useCardsStore = create<CardsState & CardsActions>(() => ({
  cards: [],
  isLoading: false,
  fetchCards: async (_noteId: string) => {
    throw new Error("not implemented");
  },
  refresh: async () => {
    throw new Error("not implemented");
  },
}));
