import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { sendMessage, startCaptureSession } from "../src/api/stream";
import CaptureScreen from "../src/screens/CaptureScreen";
import { useChatStore } from "../src/store/chat";

vi.mock("../src/api/stream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/stream")>();
  return {
    ...actual,
    sendMessage: vi.fn(),
    startCaptureSession: vi.fn(),
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

async function waitForFrame(
  lastFrame: () => string | undefined,
  predicate: (frame: string) => boolean,
): Promise<string> {
  let frame = "";
  await waitFor(() => {
    frame = lastFrame() ?? "";
    return predicate(frame);
  });
  return frame;
}

async function submitMessage(
  stdin: { write: (data: string) => void },
  text: string,
): Promise<void> {
  stdin.write(text);
  await new Promise((resolve) => setTimeout(resolve, 30));
  stdin.write("\r");
}

describe("CaptureScreen", () => {
  beforeEach(() => {
    useChatStore.setState({
      sessionId: "sess-1",
      topic: null,
      transcript: [],
      currentReply: "",
      isStreaming: false,
    });
    vi.mocked(startCaptureSession).mockResolvedValue({ sessionId: "sess-1" });
    vi.mocked(sendMessage).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the user's message immediately after typing and submitting", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield {
        type: "done",
        messageId: "m1",
        content: "Agent reply",
        topic: "First topic",
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "My question");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("My question"),
    );
    expect(frame).toContain("My question");
  });

  it("renders streamed reply fragments incrementally before the turn completes", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield { type: "delta", text: "Hel" };
      await new Promise((resolve) => setTimeout(resolve, 40));
      yield { type: "delta", text: "lo" };
      await new Promise((resolve) => setTimeout(resolve, 40));
      yield {
        type: "done",
        messageId: "m1",
        content: "Hello",
        topic: "TCP handshakes",
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "Hi");

    const partialFrame = await waitForFrame(
      lastFrame,
      (f) => f.includes("Hel") && !f.includes("Hello"),
    );
    expect(partialFrame).toMatch(/Hel/);

    const finalFrame = await waitForFrame(lastFrame, (f) =>
      f.includes("Hello"),
    );
    expect(finalFrame).toContain("Hello");
  });

  it("shows the server's canonical reply in the transcript and clears the in-flight line", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield { type: "delta", text: "partial-wrong" };
      yield {
        type: "done",
        messageId: "m1",
        content: "Canonical server reply",
        topic: "TCP handshakes",
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "Explain TCP");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("Canonical server reply"),
    );
    expect(frame).toContain("Canonical server reply");
    expect(frame).not.toContain("partial-wrong");
  });

  it("updates the displayed topic after the first turn completes", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield {
        type: "done",
        messageId: "m1",
        content: "First reply",
        topic: "TCP handshakes",
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "How does TCP work?");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("TCP handshakes"),
    );
    expect(frame).toContain("TCP handshakes");
  });
});
