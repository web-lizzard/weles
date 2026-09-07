import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteDetail } from "../src/api/notes";
import { getNote } from "../src/api/notes";
import {
  approveNote,
  sendMessage,
  startCaptureSession,
} from "../src/api/stream";
import App from "../src/app";
import { useChatStore } from "../src/store/chat";
import { useAppStore } from "../src/store/index";
import { useNotesStore } from "../src/store/notes";

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

vi.mock("../src/api/notes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/notes")>();
  return {
    ...actual,
    getNote: vi.fn(),
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
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
    });
    useNotesStore.setState({ items: [], isLoading: false, error: null });
    vi.mocked(startCaptureSession).mockResolvedValue({ sessionId: "sess-1" });
    vi.mocked(sendMessage).mockReset();
    vi.mocked(approveNote).mockReset();
    vi.mocked(getNote).mockReset();
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
});
