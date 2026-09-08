import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Card } from "../src/api/cards";
import CardDetailScreen from "../src/screens/CardDetailScreen";
import { useCardsStore } from "../src/store/cards";
import { useAppStore } from "../src/store/index";
import { useNotesStore } from "../src/store/notes";

const LEFT_ARROW = "\x1B[D";

const NOTE_ID = "00000000-0000-4000-8000-000000000001";

const CARD: Card = {
  cardId: "00000000-0000-4000-8000-000000000101",
  front: "What is a SYN?",
  back: "The first packet of a TCP handshake.",
  anchorQuote: "The client sends SYN",
  createdAt: "2026-09-06T12:00:00Z",
};

async function pressKey(
  stdin: { write: (data: string) => void },
  key: string,
): Promise<void> {
  stdin.write(key);
  await new Promise((resolve) => setTimeout(resolve, 30));
}

describe("CardDetailScreen", () => {
  beforeEach(() => {
    useAppStore.setState({
      isNotesOverlayOpen: true,
      selectedIndex: 0,
      isDetailOpen: true,
      selectedNoteId: NOTE_ID,
      activeNoteTab: "cards",
      selectedCardId: CARD.cardId,
    });
    useNotesStore.setState({
      items: [
        {
          noteId: NOTE_ID,
          topicLabel: "TCP handshakes",
          distillationStatus: "ready",
          cardCount: 1,
          lastUpdatedAt: "2026-09-06T12:00:00Z",
        },
      ],
      isLoading: false,
      error: null,
    });
    useCardsStore.setState({ cards: [CARD], isLoading: false });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the selected card in full with the tab strip still visible", () => {
    const { lastFrame } = render(<CardDetailScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("Note");
    expect(frame).toContain("Cards");
    expect(frame).toContain("What is a SYN?");
    expect(frame).toContain("The first packet of a TCP handshake.");
    expect(frame).toContain("The client sends SYN");
  });

  it("returns to the card list on left arrow without leaving the cards tab", async () => {
    const { stdin } = render(<CardDetailScreen />);

    await pressKey(stdin, LEFT_ARROW);

    expect(useAppStore.getState().selectedCardId).toBeNull();
    expect(useAppStore.getState().activeNoteTab).toBe("cards");
    expect(useAppStore.getState().isDetailOpen).toBe(true);
  });
});
