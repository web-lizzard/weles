import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Card } from "../src/api/cards";
import { listCards } from "../src/api/cards";
import type { NoteDetail, NoteListItem } from "../src/api/notes";
import { getNote } from "../src/api/notes";
import {
  approveNote,
  sendMessage,
  startCaptureSession,
} from "../src/api/stream";
import App from "../src/app";
import CardListScreen from "../src/screens/CardListScreen";
import NoteDetailScreen from "../src/screens/NoteDetailScreen";
import { useCardsStore } from "../src/store/cards";
import { useChatStore } from "../src/store/chat";
import { useAppStore } from "../src/store/index";
import { useNoteDetailStore } from "../src/store/noteDetail";
import { useNotesStore } from "../src/store/notes";

const RIGHT_ARROW = "\x1B[C";
const LEFT_ARROW = "\x1B[D";
const ESC = "\x1B";

const NOTE_ID = "00000000-0000-4000-8000-000000000001";

const NOTE_ITEM: NoteListItem = {
  noteId: NOTE_ID,
  topicLabel: "TCP handshakes",
  distillationStatus: "ready",
  cardCount: 2,
  lastUpdatedAt: "2026-09-06T12:00:00Z",
};

const NOTE_DETAIL: NoteDetail = {
  noteId: NOTE_ID,
  topic: {
    id: "00000000-0000-4000-8000-000000000010",
    label: "TCP handshakes",
  },
  content: "Full note content for the detail view",
  blocks: [],
  tags: [],
  distillationStatus: "ready",
  approvedAt: "2026-09-06T12:00:00Z",
  createdAt: "2026-09-06T12:00:00Z",
  updatedAt: "2026-09-06T12:00:00Z",
};

const CARD: Card = {
  cardId: "00000000-0000-4000-8000-000000000101",
  front: "What is a SYN?",
  back: "The first packet of a TCP handshake.",
  anchorQuote: "The client sends SYN",
  anchorLocation: null,
  createdAt: "2026-09-06T12:00:00Z",
};

vi.mock("../src/api/stream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/stream")>();
  return {
    ...actual,
    sendMessage: vi.fn(),
    startCaptureSession: vi.fn(),
    approveNote: vi.fn(),
  };
});

vi.mock("../src/hooks/useNotesPolling", () => ({
  useNotesPolling: vi.fn(),
}));

vi.mock("../src/api/notes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/notes")>();
  return {
    ...actual,
    getNote: vi.fn(),
  };
});

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

function seedOpenNote(cardCount: number) {
  useAppStore.setState({
    isNotesOverlayOpen: true,
    selectedIndex: 0,
    isDetailOpen: true,
    selectedNoteId: NOTE_ID,
    activeNoteTab: "note",
    selectedCardId: null,
  });
  useNotesStore.setState({
    items: [{ ...NOTE_ITEM, cardCount }],
    isLoading: false,
    error: null,
  });
  useNoteDetailStore.setState({ note: NOTE_DETAIL, isLoading: false });
  useCardsStore.setState({
    cards: cardCount > 0 ? [CARD] : [],
    isLoading: false,
  });
}

describe("note tab navigation", () => {
  beforeEach(() => {
    useChatStore.setState({
      sessionId: "sess-1",
      topic: null,
      coverageConfidence: null,
      transcript: [],
      currentReply: "",
      isStreaming: false,
      streamError: null,
      draft: null,
      approved: false,
      approvalReceipt: false,
    });
    useAppStore.setState({
      isNotesOverlayOpen: false,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
      activeNoteTab: "note",
      selectedCardId: null,
    });
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    useNoteDetailStore.setState({ note: null, isLoading: false });
    useCardsStore.setState({ cards: [], isLoading: false });
    vi.mocked(startCaptureSession).mockResolvedValue({ sessionId: "sess-1" });
    vi.mocked(sendMessage).mockReset();
    vi.mocked(approveNote).mockReset();
    vi.mocked(getNote).mockReset();
    vi.mocked(listCards).mockReset();
    vi.mocked(getNote).mockResolvedValue(NOTE_DETAIL);
    vi.mocked(listCards).mockResolvedValue([CARD]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("activates the cards tab on right arrow when the note has cards", async () => {
    seedOpenNote(2);
    const { stdin, lastFrame } = render(<NoteDetailScreen />);

    await pressKey(stdin, RIGHT_ARROW);

    expect(useAppStore.getState().activeNoteTab).toBe("cards");
    expect(lastFrame()).toContain("Note");
    expect(lastFrame()).toContain("Cards");
  });

  it("leaves the note tab unchanged on right arrow when the note has zero cards", async () => {
    seedOpenNote(0);
    const { stdin } = render(<NoteDetailScreen />);

    await pressKey(stdin, RIGHT_ARROW);

    expect(useAppStore.getState().activeNoteTab).toBe("note");
  });

  it("returns to the note tab on left arrow from the cards list", async () => {
    seedOpenNote(2);
    useAppStore.setState({ activeNoteTab: "cards" });
    const { stdin } = render(<CardListScreen />);

    await pressKey(stdin, LEFT_ARROW);

    expect(useAppStore.getState().activeNoteTab).toBe("note");
    expect(useAppStore.getState().selectedCardId).toBeNull();
    expect(useAppStore.getState().isDetailOpen).toBe(true);
  });

  it("shows the card list or card detail body for the current tab and depth", async () => {
    seedOpenNote(2);
    useAppStore.setState({ activeNoteTab: "cards" });
    const { lastFrame, rerender } = render(<App />);

    await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));
    expect(lastFrame()).toContain("What is a SYN?");
    expect(lastFrame()).not.toContain("Full note content for the detail view");

    useAppStore.setState({ selectedCardId: CARD.cardId });
    rerender(<App />);

    expect(lastFrame()).toContain("The first packet of a TCP handshake.");
    expect(lastFrame()).toContain("Cards");
  });

  it("renders the active tab with a blue background", () => {
    seedOpenNote(2);
    const { lastFrame } = render(<NoteDetailScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("Note");
    expect(frame).toContain("Cards");
    const ansiEsc = String.fromCharCode(27);
    expect(
      frame.includes(`${ansiEsc}[44m`) || frame.includes(`${ansiEsc}[104m`),
    ).toBe(true);
  });

  it("returns to the note list on ESC from the cards tab and from card detail", async () => {
    seedOpenNote(2);
    useAppStore.setState({ activeNoteTab: "cards", selectedCardId: null });
    const { stdin } = render(<App />);

    await pressKey(stdin, ESC);

    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useAppStore.getState().isNotesOverlayOpen).toBe(true);

    seedOpenNote(2);
    useAppStore.setState({
      isNotesOverlayOpen: true,
      isDetailOpen: true,
      selectedNoteId: NOTE_ID,
      activeNoteTab: "cards",
      selectedCardId: CARD.cardId,
    });
    await pressKey(stdin, ESC);

    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useAppStore.getState().isNotesOverlayOpen).toBe(true);
    expect(useAppStore.getState().selectedCardId).toBeNull();
  });
});
