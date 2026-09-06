import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  approveNote,
  sendMessage,
  startCaptureSession,
} from "../src/api/stream";
import App from "../src/app";
import { useChatStore } from "../src/store/chat";
import { useAppStore } from "../src/store/index";

vi.mock("../src/api/stream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/stream")>();
  return {
    ...actual,
    sendMessage: vi.fn(),
    startCaptureSession: vi.fn(),
    approveNote: vi.fn(),
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
    useAppStore.setState({ isNotesOverlayOpen: false });
    vi.mocked(startCaptureSession).mockResolvedValue({ sessionId: "sess-1" });
    vi.mocked(sendMessage).mockReset();
    vi.mocked(approveNote).mockReset();
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
      const { stdin } = render(<App />);

      await submitMessage(stdin, "/notes");
      await waitFor(() => useAppStore.getState().isNotesOverlayOpen);

      expect(useAppStore.getState().isNotesOverlayOpen).toBe(true);
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
  });
});
