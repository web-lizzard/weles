import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteDetail } from "../src/api/notes";
import { getNote } from "../src/api/notes";
import {
  fetchCardSource,
  gradeCard,
  openSitting,
  revealBack,
} from "../src/api/sittings";
import {
  approveNote,
  sendMessage,
  startCaptureSession,
} from "../src/api/stream";
import App from "../src/app";
import { useDuePolling } from "../src/hooks/useDuePolling";
import { useChatStore } from "../src/store/chat";
import { useDueStore } from "../src/store/due";
import { useAppStore } from "../src/store/index";
import { useNotesStore } from "../src/store/notes";
import { useSittingStore } from "../src/store/sitting";

const DUE_PARTITION = {
  total: 4,
  notYetSeen: 4,
  seenStillOwed: 0,
  ripeOutsideSitting: 0,
};

const DOWN_ARROW = "\x1B[B";
const ENTER = "\r";

const READY_NOTE_ID = "00000000-0000-4000-8000-000000000002";

const NOTE_DETAIL: NoteDetail = {
  noteId: READY_NOTE_ID,
  topic: {
    id: "00000000-0000-4000-8000-000000000010",
    label: "DNS resolution",
  },
  content: "Full note content shown in the detail view",
  blocks: [],
  tags: [{ id: "00000000-0000-4000-8000-000000000020", label: "networking" }],
  distillationStatus: "ready",
  approvedAt: "2026-09-06T12:00:00Z",
  createdAt: "2026-09-06T12:00:00Z",
  updatedAt: "2026-09-06T12:00:00Z",
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

vi.mock("../src/hooks/useDuePolling", () => ({
  useDuePolling: vi.fn(),
}));

vi.mock("../src/api/notes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/notes")>();
  return {
    ...actual,
    getNote: vi.fn(),
  };
});

vi.mock("../src/api/sittings", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/sittings")>();
  return {
    ...actual,
    openSitting: vi.fn(),
    revealBack: vi.fn(),
    fetchCardSource: vi.fn(),
    gradeCard: vi.fn(),
    rejectCard: vi.fn(),
  };
});

const sittingId = "00000000-0000-4000-8000-000000000001";
const cardId = "00000000-0000-4000-8000-000000000101";

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

async function submitMessage(
  stdin: { write: (data: string) => void },
  text: string,
): Promise<void> {
  stdin.write(text);
  await new Promise((resolve) => setTimeout(resolve, 30));
  stdin.write("\r");
}

async function pressKey(
  stdin: { write: (data: string) => void },
  key: string,
): Promise<void> {
  stdin.write(key);
  await new Promise((resolve) => setTimeout(resolve, 30));
}

describe("App", () => {
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
      isSittingOverlayOpen: false,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
    });
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    useSittingStore.setState({
      phase: "opening",
      sittingId: null,
      cardId: null,
      front: null,
      back: null,
      isBackVisible: false,
      selectedGradeIndex: 0,
      isSubmitting: false,
      error: null,
      lastAction: null,
    });
    useDueStore.setState({ partition: null, isStale: false });
    vi.mocked(useDuePolling).mockReset();
    vi.mocked(startCaptureSession).mockResolvedValue({ sessionId: "sess-1" });
    vi.mocked(sendMessage).mockReset();
    vi.mocked(approveNote).mockReset();
    vi.mocked(getNote).mockReset();
    vi.mocked(openSitting).mockReset();
    vi.mocked(gradeCard).mockReset().mockResolvedValue({
      sittingId: "00000000-0000-4000-8000-000000000001",
      sittingComplete: false,
      outstandingCount: 0,
      nextCardId: null,
      nextFront: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the capture screen input prompt", () => {
    const { lastFrame } = render(<App />);

    expect(lastFrame()).toContain("Weles");
  });

  it("renders a non-empty bootstrap frame", () => {
    const { lastFrame } = render(<App />);

    expect(lastFrame()).toBeTruthy();
  });

  describe("notes overlay dispatch", () => {
    it("opens the notes overlay when /notes is submitted", async () => {
      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      expect(useAppStore.getState().isNotesOverlayOpen).toBe(true);
      expect(lastFrame()).toContain("← ESC to go back");
      expect(sendMessage).not.toHaveBeenCalled();
    });

    it("closes the notes overlay when ESC is pressed", async () => {
      const { stdin } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      stdin.write("\x1B");
      await waitFor(() => !useAppStore.getState().isNotesOverlayOpen);

      expect(useAppStore.getState().isNotesOverlayOpen).toBe(false);
    });

    it("blocks capture input while the notes overlay is open", async () => {
      const { stdin } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      await submitMessage(stdin, "hello while overlay open");

      expect(sendMessage).not.toHaveBeenCalled();
    });

    it("leaves every chat store field unchanged across a /notes open/close cycle", async () => {
      const seeded = {
        sessionId: "sess-1",
        topic: "TCP handshakes",
        coverageConfidence: 0.5,
        transcript: [{ role: "user" as const, content: "Hi" }],
        currentReply: "",
        draft: {
          topic: "draft-topic",
          tags: [{ label: "draft-tag", reused: true }],
          content: "draft-body",
          noteId: null,
        },
        isStreaming: false,
      };
      useChatStore.setState(seeded);

      const { stdin } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      stdin.write("\x1B");
      await waitFor(() => !useAppStore.getState().isNotesOverlayOpen);

      const after = useChatStore.getState();
      expect(after.sessionId).toBe(seeded.sessionId);
      expect(after.topic).toBe(seeded.topic);
      expect(after.coverageConfidence).toBe(seeded.coverageConfidence);
      expect(after.transcript).toEqual(seeded.transcript);
      expect(after.draft).toEqual(seeded.draft);
      expect(after.currentReply).toBe(seeded.currentReply);
      expect(after.isStreaming).toBe(seeded.isStreaming);
    });

    it("opens note detail content after selecting a ready note with arrow and Enter", async () => {
      useNotesStore.setState({
        items: [
          {
            noteId: "00000000-0000-4000-8000-000000000001",
            topicLabel: "TCP handshakes",
            distillationStatus: "generating",
            cardCount: 0,
            lastUpdatedAt: "2026-09-06T12:00:00Z",
          },
          {
            noteId: READY_NOTE_ID,
            topicLabel: "DNS resolution",
            distillationStatus: "ready",
            cardCount: 0,
            lastUpdatedAt: "2026-09-06T11:00:00Z",
          },
        ],
        isLoading: false,
        error: null,
      });
      vi.mocked(getNote).mockResolvedValue(NOTE_DETAIL);

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      await pressKey(stdin, DOWN_ARROW);
      await pressKey(stdin, ENTER);
      await waitFor(() => useAppStore.getState().isDetailOpen);

      await waitFor(() =>
        (lastFrame() ?? "").includes(
          "Full note content shown in the detail view",
        ),
      );

      expect(lastFrame()).toContain("DNS resolution");
      expect(lastFrame()).toContain("networking");
    });

    it("returns to the list on ESC from detail and closes the overlay on a second ESC without changing chat state", async () => {
      const seeded = {
        sessionId: "sess-1",
        topic: "TCP handshakes",
        coverageConfidence: 0.5,
        transcript: [{ role: "user" as const, content: "Hi" }],
        currentReply: "",
        draft: null,
        isStreaming: false,
      };
      useChatStore.setState(seeded);
      useNotesStore.setState({
        items: [
          {
            noteId: READY_NOTE_ID,
            topicLabel: "DNS resolution",
            distillationStatus: "ready",
            cardCount: 0,
            lastUpdatedAt: "2026-09-06T11:00:00Z",
          },
        ],
        isLoading: false,
        error: null,
      });
      vi.mocked(getNote).mockResolvedValue(NOTE_DETAIL);

      const { stdin } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      await pressKey(stdin, ENTER);
      await waitFor(() => useAppStore.getState().isDetailOpen);

      const chatBeforeEsc = useChatStore.getState();

      stdin.write("\x1B");
      await waitFor(() => !useAppStore.getState().isDetailOpen);
      expect(useAppStore.getState().isNotesOverlayOpen).toBe(true);
      expect(useChatStore.getState()).toEqual(chatBeforeEsc);

      stdin.write("\x1B");
      await waitFor(() => !useAppStore.getState().isNotesOverlayOpen);
      expect(useChatStore.getState()).toEqual(chatBeforeEsc);
    });
  });

  describe("due count shell row", () => {
    it("starts due polling at fifteen seconds when the shell mounts", () => {
      render(<App />);

      expect(useDuePolling).toHaveBeenCalledWith(15_000);
    });

    it("shows no due-count line while the partition is still null", () => {
      const { lastFrame } = render(<App />);

      expect(lastFrame() ?? "").not.toMatch(/\d+ cards due/);
    });

    it("shows the partition total in a footer row below the capture screen", () => {
      useDueStore.setState({ partition: DUE_PARTITION, isStale: false });

      const { lastFrame } = render(<App />);
      const frame = lastFrame() ?? "";
      const lines = frame.split("\n");
      const ruleIndexes = lines.reduce<number[]>((acc, line, index) => {
        if (/^─+$/.test(line)) {
          acc.push(index);
        }
        return acc;
      }, []);
      const dueLineIndex = lines.findIndex((line) =>
        line.includes("4 cards due"),
      );

      expect(dueLineIndex).toBeGreaterThanOrEqual(0);
      // The input frame brackets the input row with a rule above and below it
      // (tui/src/components/InputFrame.tsx); the due line sits below both.
      expect(ruleIndexes.length).toBeGreaterThanOrEqual(2);
      expect(dueLineIndex).toBeGreaterThan(ruleIndexes[ruleIndexes.length - 1]);
    });

    it("hides the due-count status line while the notes panel is open", async () => {
      useDueStore.setState({ partition: DUE_PARTITION, isStale: false });

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      const frame = lastFrame() ?? "";

      // The status line (and its due count) is replaced by the notes panel's
      // own bottom hint line while the panel is open (Phase 14 Contract #1).
      expect(frame).not.toContain("4 cards due");
      expect(frame).toContain("↑↓ select · Enter open · ← ESC to go back");
    });

    it("shows the due count in the sitting overlay footer instead of the shell row", async () => {
      useDueStore.setState({ partition: DUE_PARTITION, isStale: false });
      vi.mocked(openSitting).mockResolvedValue({
        kind: "opened",
        sittingId,
        cardId,
        front: "What is a SYN?",
        sittingComplete: false,
        outstandingCount: 0,
      });

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/remember");
      await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));

      const frame = lastFrame() ?? "";
      const dueIndex = frame.indexOf("4 cards due");
      const cardIndex = frame.indexOf("What is a SYN?");

      expect(dueIndex).toBeGreaterThanOrEqual(0);
      expect(dueIndex).toBeGreaterThan(cardIndex);
      expect(frame.match(/4 cards due/g)?.length).toBe(1);
    });
  });

  describe("remember sitting overlay dispatch", () => {
    it("opens the sitting overlay when /remember is submitted", async () => {
      vi.mocked(openSitting).mockResolvedValue({
        kind: "opened",
        sittingId,
        cardId,
        front: "What is a SYN?",
        sittingComplete: false,
        outstandingCount: 0,
      });

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/remember");
      await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));

      expect(lastFrame()).toContain("1 Forgot");
      expect(lastFrame()).toContain("← ESC to go back");
      expect(lastFrame()).toContain("Press t to toggle card");
      expect(sendMessage).not.toHaveBeenCalled();
      expect(openSitting).toHaveBeenCalledTimes(1);
    });

    it("closes the sitting overlay on ESC and resets the sitting store", async () => {
      vi.mocked(openSitting).mockResolvedValue({
        kind: "opened",
        sittingId,
        cardId,
        front: "What is a SYN?",
        sittingComplete: false,
        outstandingCount: 0,
      });

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/remember");
      await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));

      stdin.write("\x1B");
      await waitFor(() => !(lastFrame() ?? "").includes("What is a SYN?"));

      const sitting = useSittingStore.getState();
      expect(sitting.phase).toBe("opening");
      expect(sitting.sittingId).toBeNull();
      expect(sitting.cardId).toBeNull();
      expect(sitting.front).toBeNull();
    });

    it("opens a new sitting after ESC during loading left a stale open in flight", async () => {
      let resolveOpen: (
        value: Awaited<ReturnType<typeof openSitting>>,
      ) => void = () => {};
      vi.mocked(openSitting)
        .mockImplementationOnce(
          () =>
            new Promise((resolve) => {
              resolveOpen = resolve;
            }),
        )
        .mockResolvedValueOnce({
          kind: "opened",
          sittingId,
          cardId,
          front: "After reopen",
          sittingComplete: false,
          outstandingCount: 0,
        });

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/remember");
      await waitFor(() => (lastFrame() ?? "").includes("Loading..."));

      stdin.write("\x1B");
      await waitFor(() => !(lastFrame() ?? "").includes("Loading..."));

      resolveOpen({
        kind: "opened",
        sittingId,
        cardId,
        front: "Stale card",
        sittingComplete: false,
        outstandingCount: 0,
      });
      await waitFor(
        () => useAppStore.getState().isSittingOverlayOpen === false,
      );

      await submitMessage(stdin, "/remember");
      await waitFor(() => (lastFrame() ?? "").includes("After reopen"));

      expect(openSitting).toHaveBeenCalledTimes(2);
    });

    it("closes the source view on ESC before leaving the sitting overlay", async () => {
      vi.mocked(openSitting).mockResolvedValue({
        kind: "opened",
        sittingId,
        cardId,
        front: "What is a SYN?",
        sittingComplete: false,
        outstandingCount: 0,
      });
      vi.mocked(revealBack).mockResolvedValue({
        sittingId,
        cardId,
        front: "What is a SYN?",
        back: "Synchronize sequence numbers.",
      });
      vi.mocked(fetchCardSource).mockResolvedValue({
        blocks: [
          { index: 0, text: "Context above." },
          { index: 1, text: "Quoted span text" },
        ],
        span: { blockIndex: 1, start: 0, end: 6 },
      });

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/remember");
      await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));

      stdin.write("t");
      await waitFor(() =>
        (lastFrame() ?? "").includes("Synchronize sequence numbers."),
      );

      stdin.write("s");
      await waitFor(() => (lastFrame() ?? "").includes("Context above."));

      expect(useAppStore.getState().isSittingOverlayOpen).toBe(true);

      stdin.write("\x1B");
      await waitFor(() => !(lastFrame() ?? "").includes("Context above."));
      expect(lastFrame()).toContain("Synchronize sequence numbers.");
      expect(useAppStore.getState().isSittingOverlayOpen).toBe(true);

      stdin.write("\x1B");
      await waitFor(() => !(lastFrame() ?? "").includes("What is a SYN?"));
      expect(useAppStore.getState().isSittingOverlayOpen).toBe(false);
    });

    it("blocks capture input while the sitting overlay is open", async () => {
      vi.mocked(openSitting).mockResolvedValue({
        kind: "opened",
        sittingId,
        cardId,
        front: "What is a SYN?",
        sittingComplete: false,
        outstandingCount: 0,
      });

      const { stdin, lastFrame } = render(<App />);

      await submitMessage(stdin, "/remember");
      await waitFor(() => (lastFrame() ?? "").includes("What is a SYN?"));

      await submitMessage(stdin, "hello while overlay open");

      expect(sendMessage).not.toHaveBeenCalled();
      expect(lastFrame()).toContain("What is a SYN?");
    });
  });
});
