import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Card } from "../src/api/cards";
import { listCards } from "../src/api/cards";
import { useCardsStore } from "../src/store/cards";
import { useAppStore } from "../src/store/index";
import { useNotesStore } from "../src/store/notes";

vi.mock("../src/api/cards", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/cards")>();
  return {
    ...actual,
    listCards: vi.fn(),
  };
});

const NOTE_ID = "00000000-0000-4000-8000-000000000001";

const CARD: Card = {
  cardId: "00000000-0000-4000-8000-000000000101",
  front: "What is a SYN?",
  back: "The first packet of a TCP handshake.",
  anchorQuote: "The client sends SYN",
  createdAt: "2026-09-06T12:00:00Z",
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("useCardsStore", () => {
  beforeEach(() => {
    useCardsStore.setState({ cards: [], isLoading: false });
    useAppStore.setState({
      isNotesOverlayOpen: false,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
    });
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    vi.mocked(listCards).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("populates cards and clears loading after a successful fetchCards", async () => {
    vi.mocked(listCards).mockResolvedValue([CARD]);

    await useCardsStore.getState().fetchCards(NOTE_ID);

    expect(useCardsStore.getState().cards).toEqual([CARD]);
    expect(useCardsStore.getState().isLoading).toBe(false);
  });

  it("clears loading, leaves the note view, and sets the notes banner when fetchCards fails", async () => {
    useAppStore.setState({
      isDetailOpen: true,
      selectedNoteId: NOTE_ID,
    });
    vi.mocked(listCards).mockRejectedValue(new Error("Note not found"));

    await useCardsStore.getState().fetchCards(NOTE_ID);

    expect(useCardsStore.getState().isLoading).toBe(false);
    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useNotesStore.getState().error).toBe("Note not found");
  });

  it("re-fetches the selected note on refresh without clearing the visible list", async () => {
    const refreshed: Card = {
      ...CARD,
      back: "Updated back",
    };
    useAppStore.setState({
      isDetailOpen: true,
      selectedNoteId: NOTE_ID,
    });
    useCardsStore.setState({ cards: [CARD], isLoading: false });

    const pending = deferred<Card[]>();
    vi.mocked(listCards).mockReturnValue(pending.promise);

    const refreshPromise = useCardsStore.getState().refresh();
    const cardsWhilePending = useCardsStore.getState().cards;

    pending.resolve([refreshed]);
    await refreshPromise;

    expect(cardsWhilePending).toEqual([CARD]);
    expect(listCards).toHaveBeenCalledWith(NOTE_ID);
    expect(useCardsStore.getState().cards).toEqual([refreshed]);
    expect(useCardsStore.getState().isLoading).toBe(false);
  });
});
