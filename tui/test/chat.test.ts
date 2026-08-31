import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReplyStreamEvent } from "../src/api/stream";
import { SendMessageHttpError, sendMessage } from "../src/api/stream";
import { useChatStore } from "../src/store/chat";

type StreamError = { code: string; detail: string } | null;

function getStreamError(): StreamError {
  return (
    (useChatStore.getState() as { streamError?: StreamError }).streamError ??
    null
  );
}

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

function failingStream(error: unknown): AsyncGenerator<ReplyStreamEvent> {
  const iterator = {
    next() {
      return Promise.reject(error);
    },
    [Symbol.asyncIterator]() {
      return this;
    },
  } as AsyncGenerator<ReplyStreamEvent>;
  return iterator;
}

describe("useChatStore", () => {
  beforeEach(() => {
    useChatStore.setState({
      sessionId: "sess-1",
      topic: null,
      coverageConfidence: null,
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
          coverageConfidence: 0,
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
        coverageConfidence: 0,
      };
    });

    await useChatStore.getState().sendUserMessage("Hi");

    expect(useChatStore.getState().currentReply).toBe("");
  });

  it("sets coverageConfidence when a done event is received", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      streamEvents([
        {
          type: "done",
          messageId: "m1",
          content: "Reply",
          topic: "Topic",
          coverageConfidence: 0.75,
        },
      ]),
    );

    await useChatStore.getState().sendUserMessage("My question");

    expect(useChatStore.getState().coverageConfidence).toBe(0.75);
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
          coverageConfidence: 0,
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

  it("sets streamError when an in-band error event is received", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      streamEvents([
        {
          type: "error",
          code: "capture_session_closed",
          detail: "Session is closed",
        },
      ]),
    );

    await useChatStore.getState().sendUserMessage("Hi");

    expect(getStreamError()).toEqual({
      code: "capture_session_closed",
      detail: "Session is closed",
    });
    expect(useChatStore.getState().transcript).toEqual([
      { role: "user", content: "Hi" },
    ]);
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it("sets streamError from SendMessageHttpError on pre-stream failure", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      failingStream(
        new SendMessageHttpError(
          "capture_session_not_found",
          "Capture session not found",
          404,
        ),
      ),
    );

    await useChatStore.getState().sendUserMessage("Hi");

    expect(getStreamError()).toEqual({
      code: "capture_session_not_found",
      detail: "Capture session not found",
    });
    expect(useChatStore.getState().transcript).toEqual([
      { role: "user", content: "Hi" },
    ]);
  });

  it("clears streamError when sending a new message", async () => {
    useChatStore.setState({
      streamError: { code: "old_error", detail: "Old problem" },
    } as Parameters<typeof useChatStore.setState>[0]);

    vi.mocked(sendMessage).mockImplementation(() =>
      streamEvents([
        {
          type: "done",
          messageId: "m1",
          content: "Ok",
          topic: "Topic",
          coverageConfidence: 0,
        },
      ]),
    );

    await useChatStore.getState().sendUserMessage("Hi");

    expect(getStreamError()).toBeNull();
  });

  it("maps unknown thrown errors to a generic streamError fallback", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      failingStream(new Error("network down")),
    );

    await useChatStore.getState().sendUserMessage("Hi");

    expect(getStreamError()).toEqual({
      code: "unknown_error",
      detail: "network down",
    });
  });
});
