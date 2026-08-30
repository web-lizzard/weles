import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReplyStreamEvent } from "../src/api/stream";
import { sendMessage } from "../src/api/stream";
import { useChatStore } from "../src/store/chat";

vi.mock("../src/api/stream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/stream")>();
  return {
    ...actual,
    sendMessage: vi.fn(),
    startCaptureSession: vi.fn(),
  };
});

async function* streamEvents(
  events: ReplyStreamEvent[],
): AsyncGenerator<ReplyStreamEvent> {
  for (const event of events) {
    yield event;
  }
}

describe("useChatStore", () => {
  beforeEach(() => {
    useChatStore.setState({
      sessionId: "sess-1",
      topic: null,
      transcript: [],
      currentReply: "",
      isStreaming: false,
    });
    vi.mocked(sendMessage).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("appends the user message to transcript when sending", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      streamEvents([
        {
          type: "done",
          messageId: "m1",
          content: "Reply",
          topic: "Topic",
        },
      ]),
    );

    await useChatStore.getState().sendUserMessage("My question");

    expect(useChatStore.getState().transcript).toEqual([
      { role: "user", content: "My question" },
      { role: "agent", content: "Reply" },
    ]);
  });

  it("accumulates delta text in currentReply while streaming", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield { type: "delta", text: "Hel" };
      expect(useChatStore.getState().currentReply).toBe("Hel");
      yield { type: "delta", text: "lo" };
      expect(useChatStore.getState().currentReply).toBe("Hello");
      yield {
        type: "done",
        messageId: "m1",
        content: "Hello",
        topic: "Topic",
      };
    });

    await useChatStore.getState().sendUserMessage("Hi");

    expect(useChatStore.getState().currentReply).toBe("");
  });

  it("uses server done content for the agent transcript entry and sets topic", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      streamEvents([
        { type: "delta", text: "partial" },
        {
          type: "done",
          messageId: "m1",
          content: "Canonical server reply",
          topic: "TCP handshakes",
        },
      ]),
    );

    await useChatStore.getState().sendUserMessage("Explain TCP");

    const state = useChatStore.getState();
    expect(state.transcript).toEqual([
      { role: "user", content: "Explain TCP" },
      { role: "agent", content: "Canonical server reply" },
    ]);
    expect(state.currentReply).toBe("");
    expect(state.topic).toBe("TCP handshakes");
  });
});
