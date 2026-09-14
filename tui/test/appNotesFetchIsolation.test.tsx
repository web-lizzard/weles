import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { startCaptureSession } from "../src/api/stream";
import App from "../src/app";
import { useChatStore } from "../src/store/chat";
import { useAppStore } from "../src/store/index";

// R1-F7
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

describe("App notes overlay network isolation (R1-F7)", () => {
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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("[]", {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("does not reach the real fetch boundary when the notes overlay mounts, under the same mocks app.test.tsx's notes-overlay tests use", async () => {
    const { stdin } = render(<App />);

    await submitMessage(stdin, "/notes");
    await waitFor(() => useAppStore.getState().isNotesOverlayOpen);
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(fetch).not.toHaveBeenCalled();
  });
});
