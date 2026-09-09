import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Card } from "../src/api/cards";
import { listCards } from "../src/api/cards";
import CardListScreen from "../src/screens/CardListScreen";
import { useCardsStore } from "../src/store/cards";
import { useAppStore } from "../src/store/index";
import { useNotesStore } from "../src/store/notes";

const UP_ARROW = "\x1B[A";
const DOWN_ARROW = "\x1B[B";
const ENTER = "\r";

const NOTE_ID = "00000000-0000-4000-8000-000000000001";

const CARDS: Card[] = [
  {
    cardId: "00000000-0000-4000-8000-000000000101",
    front: "What is a SYN?",
    back: "The first packet of a TCP handshake.",
    anchorQuote: "The client sends SYN",
    anchorLocation: null,
    createdAt: "2026-09-06T12:00:00Z",
  },
  {
    cardId: "00000000-0000-4000-8000-000000000102",
    front: "What is ACK?",
    back: "The acknowledgement flag in TCP.",
    anchorQuote: "The server replies with SYN-ACK",
    anchorLocation: null,
    createdAt: "2026-09-06T12:01:00Z",
  },
  {
    cardId: "00000000-0000-4000-8000-000000000103",
    front: "What is FIN?",
    back: "The flag that closes a TCP connection.",
    anchorQuote: "Either side may send FIN",
    anchorLocation: null,
    createdAt: "2026-09-06T12:02:00Z",
  },
];

vi.mock("../src/api/cards", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/cards")>();
  return {
    ...actual,
    listCards: vi.fn(),
  };
});

async function waitFor(
  predicate: () => boolean,
  timeoutMs = 2000,
  intervalMs = 20,
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (predicate()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("Timed out waiting for condition");
}

async function pressKey(
  stdin: { write: (data: string) => void },
  key: string,
): Promise<void> {
  stdin.write(key);
  await new Promise((resolve) => setTimeout(resolve, 30));
}

describe("CardListScreen", () => {
  beforeEach(() => {
    useAppStore.setState({
      isNotesOverlayOpen: true,
      selectedIndex: 0,
      isDetailOpen: true,
      selectedNoteId: NOTE_ID,
      activeNoteTab: "cards",
      selectedCardId: null,
    });
    useNotesStore.setState({
      items: [
        {
          noteId: NOTE_ID,
          topicLabel: "TCP handshakes",
          distillationStatus: "ready",
          cardCount: CARDS.length,
          lastUpdatedAt: "2026-09-06T12:00:00Z",
        },
      ],
      isLoading: false,
      error: null,
    });
    useCardsStore.setState({ cards: [], isLoading: false });
    vi.mocked(listCards).mockReset();
    vi.mocked(listCards).mockResolvedValue(CARDS);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a no-cards line when the list is empty", async () => {
    vi.mocked(listCards).mockResolvedValue([]);
    useNotesStore.setState({
      items: [
        {
          noteId: NOTE_ID,
          topicLabel: "TCP handshakes",
          distillationStatus: "ready",
          cardCount: 0,
          lastUpdatedAt: "2026-09-06T12:00:00Z",
        },
      ],
      isLoading: false,
      error: null,
    });

    const { lastFrame } = render(<CardListScreen />);

    expect(lastFrame()).toContain("No cards for this note");
    expect(lastFrame()).toContain("Cards");
  });

  it("moves and clamps row selection with up and down arrows, and Enter opens card detail", async () => {
    useCardsStore.setState({ cards: CARDS, isLoading: false });
    const { stdin, lastFrame } = render(<CardListScreen />);

    await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));

    await pressKey(stdin, UP_ARROW);
    await pressKey(stdin, ENTER);
    expect(useAppStore.getState().selectedCardId).toBe(CARDS[0].cardId);

    useAppStore.setState({ selectedCardId: null });
    await pressKey(stdin, DOWN_ARROW);
    await pressKey(stdin, ENTER);
    expect(useAppStore.getState().selectedCardId).toBe(CARDS[1].cardId);

    useAppStore.setState({ selectedCardId: null });
    await pressKey(stdin, DOWN_ARROW);
    await pressKey(stdin, DOWN_ARROW);
    await pressKey(stdin, DOWN_ARROW);
    await pressKey(stdin, ENTER);
    expect(useAppStore.getState().selectedCardId).toBe(CARDS[2].cardId);
    expect(lastFrame()).toContain("Cards");
  });

  it("refetches cards when r is pressed", async () => {
    useCardsStore.setState({ cards: CARDS, isLoading: false });
    vi.mocked(listCards).mockClear();
    const { stdin, lastFrame } = render(<CardListScreen />);

    await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));
    vi.mocked(listCards).mockClear();

    await pressKey(stdin, "r");

    expect(listCards).toHaveBeenCalledWith(NOTE_ID);
  });

  // R1-F1
  it("does not keep another note's cards visible while the new note's cards load", async () => {
    const otherNoteId = "00000000-0000-4000-8000-000000000002";
    const leftover: Card = {
      cardId: "00000000-0000-4000-8000-000000000199",
      front: "Leftover front from another note",
      back: "Leftover back",
      anchorQuote: "Leftover quote",
      anchorLocation: null,
      createdAt: "2026-09-06T11:00:00Z",
    };

    useAppStore.setState({ selectedNoteId: otherNoteId });
    useNotesStore.setState({
      items: [
        {
          noteId: otherNoteId,
          topicLabel: "UDP",
          distillationStatus: "ready",
          cardCount: 1,
          lastUpdatedAt: "2026-09-06T12:00:00Z",
        },
      ],
      isLoading: false,
      error: null,
    });
    useCardsStore.setState({ cards: [leftover], isLoading: false });

    vi.mocked(listCards).mockReturnValue(new Promise(() => {}));

    const { lastFrame, unmount } = render(<CardListScreen />);
    try {
      await waitFor(() => vi.mocked(listCards).mock.calls.length > 0);

      expect(lastFrame()).not.toContain("Leftover front from another note");
      expect(useCardsStore.getState().cards).toEqual([]);
      expect(listCards).toHaveBeenCalledWith(otherNoteId);
    } finally {
      unmount();
    }
  });
});
