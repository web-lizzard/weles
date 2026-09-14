import { Box } from "ink";
import { render } from "ink-testing-library";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  approveNote,
  sendMessage,
  startCaptureSession,
} from "../src/api/stream";
import CaptureScreen from "../src/screens/CaptureScreen";
import { useChatStore } from "../src/store/chat";
import { useAppStore } from "../src/store/index";

const COVERAGE_BANNER_TEXT =
  "✓ This topic seems well covered — keep going, or wrap up when you're ready.";
const UP_ARROW = "\x1B[A";
const DOWN_ARROW = "\x1B[B";

function paragraphs(prefix: string, count: number): string {
  return Array.from({ length: count }, (_, i) => `${prefix}-${i}`).join("\n\n");
}

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
      coverageConfidence: null,
      transcript: [],
      currentReply: "",
      isStreaming: false,
      streamError: null,
      draft: null,
      approved: false,
    });
    vi.mocked(startCaptureSession).mockResolvedValue({ sessionId: "sess-1" });
    vi.mocked(sendMessage).mockReset();
    vi.mocked(approveNote).mockReset();
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
        coverageConfidence: 0,
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
        coverageConfidence: 0,
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
        coverageConfidence: 0,
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
        coverageConfidence: 0,
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "How does TCP work?");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("TCP handshakes"),
    );
    expect(frame).toContain("TCP handshakes");
  });

  it("displays stream error detail in a status bar when streamError is set", () => {
    useChatStore.setState({
      streamError: {
        code: "capture_session_closed",
        detail: "Session is closed",
      },
    });

    const { lastFrame } = render(<CaptureScreen />);

    expect(lastFrame()).toContain("Session is closed");
  });

  it("shows status bar after an in-band error while sending a message", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield {
        type: "error",
        code: "capture_session_closed",
        detail: "Session is closed",
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "Hi");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("Session is closed"),
    );
    expect(frame).toContain("Session is closed");
  });

  it("hides status bar after the next successful send clears streamError", async () => {
    useChatStore.setState({
      streamError: { code: "old_error", detail: "Old problem" },
    });

    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield {
        type: "done",
        messageId: "m1",
        content: "Ok",
        topic: "Topic",
        coverageConfidence: 0,
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    expect(lastFrame()).toContain("Old problem");

    await submitMessage(stdin, "Hi");

    const frame = await waitForFrame(
      lastFrame,
      (f) => f.includes("Ok") && !f.includes("Old problem"),
    );
    expect(frame).not.toContain("Old problem");
  });

  it("shows the coverage wrap-up banner when coverageConfidence is fully covered", () => {
    useChatStore.setState({
      topic: "TCP handshakes",
      coverageConfidence: 1,
      transcript: [{ role: "user", content: "How does TCP work?" }],
    });

    const { lastFrame } = render(<CaptureScreen />);

    expect(lastFrame()).toContain(COVERAGE_BANNER_TEXT);
  });

  it("shows the coverage wrap-up banner when coverageConfidence is above one", () => {
    useChatStore.setState({
      topic: "TCP handshakes",
      coverageConfidence: 1.25,
      transcript: [{ role: "user", content: "How does TCP work?" }],
    });

    const { lastFrame } = render(<CaptureScreen />);

    expect(lastFrame()).toContain(COVERAGE_BANNER_TEXT);
  });

  it("hides the coverage wrap-up banner when coverageConfidence is null or below one", () => {
    useChatStore.setState({
      topic: "TCP handshakes",
      coverageConfidence: null,
      transcript: [{ role: "user", content: "How does TCP work?" }],
    });

    const { lastFrame, rerender } = render(<CaptureScreen />);
    expect(lastFrame()).not.toContain(COVERAGE_BANNER_TEXT);

    useChatStore.setState({ coverageConfidence: 0.75 });
    rerender(<CaptureScreen />);
    expect(lastFrame()).not.toContain(COVERAGE_BANNER_TEXT);
  });

  it("renders the coverage wrap-up banner after transcript content", () => {
    useChatStore.setState({
      topic: "TCP handshakes",
      coverageConfidence: 1,
      transcript: [{ role: "user", content: "Transcript marker line" }],
    });

    const { lastFrame } = render(<CaptureScreen />);
    const frame = lastFrame() ?? "";
    const transcriptIndex = frame.indexOf("Transcript marker line");
    const bannerIndex = frame.indexOf(COVERAGE_BANNER_TEXT);

    expect(transcriptIndex).toBeGreaterThanOrEqual(0);
    expect(bannerIndex).toBeGreaterThan(transcriptIndex);
  });

  it("still accepts a new message while the coverage wrap-up banner is visible", async () => {
    useChatStore.setState({
      topic: "TCP handshakes",
      coverageConfidence: 1,
      transcript: [{ role: "user", content: "First question" }],
    });

    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield {
        type: "done",
        messageId: "m2",
        content: "Follow-up reply",
        topic: "TCP handshakes",
        coverageConfidence: 1,
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    expect(lastFrame()).toContain(COVERAGE_BANNER_TEXT);

    await submitMessage(stdin, "Follow-up question");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("Follow-up question"),
    );
    expect(frame).toContain(COVERAGE_BANNER_TEXT);
    expect(frame).toContain("Follow-up question");
    expect(sendMessage).toHaveBeenCalled();
  });

  it("does not render the draft panel when draft is null", () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: null,
    });

    const { lastFrame } = render(<CaptureScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("Session topic");
    expect(frame).not.toContain("draft-panel-topic");
    expect(frame).not.toContain("draft-panel-tag-a");
  });

  it("renders topic and tags received so far in a partial draft", () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: {
        topic: "draft-panel-topic",
        tags: [
          { label: "draft-panel-tag-a", reused: true },
          { label: "draft-panel-tag-b", reused: true },
        ],
        content: "",
        noteId: null,
      },
    });

    const { lastFrame } = render(<CaptureScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("Topic:");
    expect(frame).toContain("draft-panel-topic");
    expect(frame).toContain("Tags:");
    expect(frame).toContain("draft-panel-tag-a");
    expect(frame).toContain("draft-panel-tag-b");
    expect(frame).not.toContain("draft-panel-body");
  });

  it("renders the draft body when the draft is complete", () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: {
        topic: "draft-panel-topic",
        tags: [{ label: "draft-panel-tag-a", reused: true }],
        content: "draft-panel-body",
        noteId: "00000000-0000-4000-8000-000000000010",
      },
    });

    const { lastFrame } = render(<CaptureScreen />);

    expect(lastFrame()).toContain("draft-panel-body");
  });

  it("marks a newly minted tag distinctly from a reused one", () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: {
        topic: "draft-panel-topic",
        tags: [
          { label: "draft-panel-tag-reused", reused: true },
          { label: "draft-panel-tag-new", reused: false },
        ],
        content: "",
        noteId: null,
      },
    });

    const { lastFrame } = render(<CaptureScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("draft-panel-tag-reused");
    expect(frame).not.toContain("draft-panel-tag-reused (new)");
    expect(frame).toContain("draft-panel-tag-new (new)");
  });

  it("keeps the input line visible when a long conversation under a topic fills a terminal-high screen", () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: Array.from({ length: 40 }, (_, i) => ({
        role: i % 2 === 0 ? ("user" as const) : ("agent" as const),
        content: `overflow-line-${i}`,
      })),
    });

    const { lastFrame } = render(
      <Box flexDirection="column" height={24}>
        <CaptureScreen />
      </Box>,
    );
    const frame = lastFrame() ?? "";

    const frameLines = frame.split("\n");
    const inputRow = frameLines
      .map((line) => line.includes("You:"))
      .lastIndexOf(true);

    expect(frame).toContain("Topic: Session topic");
    expect(frame).toContain("overflow-line-39");
    expect(frameLines.length).toBeLessThanOrEqual(24);
    expect(frameLines[inputRow - 1]).toMatch(/^─+$/);
    expect(frameLines[inputRow - 2]).toBe("");
    expect(frameLines[inputRow + 1]).toMatch(/^─+$/);
  });

  it("pins a long draft in a bounded window and shows a more-below marker", () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: {
        topic: "draft-scroll-topic",
        tags: [{ label: "draft-scroll-tag", reused: true }],
        content: paragraphs("draft-scroll-line", 15),
        noteId: null,
      },
    });

    const { lastFrame } = render(<CaptureScreen />);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("draft-scroll-line-0");
    expect(frame).not.toContain("draft-scroll-line-14");
    expect(frame).toContain("more below");
    expect(frame).not.toContain("more above");
  });

  it("scrolls the pinned draft with the arrow keys and returns to the top", async () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: {
        topic: "draft-arrow-topic",
        tags: [{ label: "draft-arrow-tag", reused: true }],
        content: paragraphs("draft-arrow-line", 15),
        noteId: null,
      },
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);

    // The draft region caps its height at floor((rows-1)/2); with the default
    // 24-row terminal that's 11 lines, well under this 15-paragraph fixture's
    // rendered line count, so pressing well past the true max offset still
    // lands on it — extra presses clamp rather than overshoot.
    const DOWN_PRESSES_PAST_MAX_OFFSET = 30;
    for (let i = 0; i < DOWN_PRESSES_PAST_MAX_OFFSET; i++) {
      stdin.write(DOWN_ARROW);
      await new Promise((resolve) => setTimeout(resolve, 10));
    }

    const scrolledFrame = lastFrame() ?? "";
    expect(scrolledFrame).toContain("more above");
    expect(scrolledFrame).toContain("draft-arrow-line-14");

    for (let i = 0; i < DOWN_PRESSES_PAST_MAX_OFFSET; i++) {
      stdin.write(UP_ARROW);
      await new Promise((resolve) => setTimeout(resolve, 10));
    }

    const topFrame = lastFrame() ?? "";
    expect(topFrame).not.toContain("more above");
    expect(topFrame).toContain("draft-arrow-line-0");
    expect(topFrame).toContain("more below");
  });

  it("resets the draft's scroll position to the top when a new draft replaces the pinned one", async () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: {
        topic: "draft-old-topic",
        tags: [{ label: "draft-old-tag", reused: true }],
        content: paragraphs("draft-old-line", 15),
        noteId: null,
      },
    });

    const { lastFrame, stdin, rerender } = render(<CaptureScreen />);

    for (let i = 0; i < 10; i++) {
      stdin.write(DOWN_ARROW);
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
    expect(lastFrame() ?? "").toContain("more above");

    useChatStore.setState({
      draft: {
        topic: "draft-new-topic",
        tags: [{ label: "draft-new-tag", reused: true }],
        content: paragraphs("draft-new-line", 15),
        noteId: null,
      },
    });
    rerender(<CaptureScreen />);

    const frame = lastFrame() ?? "";
    expect(frame).not.toContain("more above");
    expect(frame).toContain("draft-new-line-0");
    expect(frame).not.toContain("draft-new-line-14");
    expect(frame).toContain("more below");
  });

  it("renders a thick approval receipt and keeps input focused after /approve succeeds", async () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: {
        topic: "draft-panel-topic",
        tags: [{ label: "draft-panel-tag-a", reused: true }],
        content: "draft-panel-body",
        noteId: "00000000-0000-4000-8000-000000000010",
      },
    });
    vi.mocked(approveNote).mockResolvedValue({
      noteId: "00000000-0000-4000-8000-000000000010",
      topic: "draft-panel-topic",
      tags: ["draft-panel-tag-a"],
    });
    vi.mocked(startCaptureSession)
      .mockResolvedValueOnce({ sessionId: "sess-1" })
      .mockResolvedValueOnce({ sessionId: "sess-2" });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "/approve");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("✓ Approved — queued for saving"),
    );
    expect(frame).toContain("═".repeat(80));
    expect(frame).toContain("✓ Approved — queued for saving");
    expect(frame).not.toContain("draft-panel-body");
    expect(sendMessage).not.toHaveBeenCalled();
    expect(startCaptureSession).toHaveBeenCalledTimes(2);

    await submitMessage(stdin, "Next topic opener");
    const afterInput = await waitForFrame(lastFrame, (f) =>
      f.includes("Next topic opener"),
    );
    expect(afterInput).toContain("Next topic opener");
  });

  it("makes no request when /approve is submitted with no draft", async () => {
    useChatStore.setState({
      topic: "Session topic",
      transcript: [{ role: "user", content: "Transcript line" }],
      draft: null,
    });

    const { stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "/approve");
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(approveNote).not.toHaveBeenCalled();
    expect(sendMessage).not.toHaveBeenCalled();
  });

  it("sends prose containing the word approve as a normal turn instead of intercepting it", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield {
        type: "done",
        messageId: "m1",
        content: "Ok",
        topic: "Session topic",
        coverageConfidence: 0,
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "I think we should approve this plan");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("I think we should approve this plan"),
    );
    expect(frame).toContain("I think we should approve this plan");
    expect(sendMessage).toHaveBeenCalled();
    expect(approveNote).not.toHaveBeenCalled();
  });

  it("sends prose containing the word remember as a normal turn instead of opening a review", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield {
        type: "done",
        messageId: "m1",
        content: "Ok",
        topic: "Session topic",
        coverageConfidence: 0,
      };
    });

    const { lastFrame, stdin } = render(<CaptureScreen />);
    await submitMessage(stdin, "remember to ask me about TCP windows");

    const frame = await waitForFrame(lastFrame, (f) =>
      f.includes("remember to ask me about TCP windows"),
    );
    expect(frame).toContain("remember to ask me about TCP windows");
    expect(sendMessage).toHaveBeenCalled();
    expect(useAppStore.getState().isSittingOverlayOpen).toBe(false);
  });
});
