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
      draft: null,
      isStreaming: false,
      streamError: null,
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

  it("accumulates draft topic, tags, and content as drafting events arrive", async () => {
    const snapshots: Array<ReturnType<typeof useChatStore.getState>["draft"]> =
      [];

    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield { type: "draft_topic", label: "TCP congestion", reused: false };
      snapshots.push(useChatStore.getState().draft);

      yield { type: "draft_tag", label: "networking", reused: true };
      yield { type: "draft_tag", label: "tcp", reused: false };
      snapshots.push(useChatStore.getState().draft);

      yield { type: "draft_delta", text: "Notes about " };
      yield { type: "draft_delta", text: "TCP." };
      snapshots.push(useChatStore.getState().draft);

      yield {
        type: "draft_done",
        noteId: "00000000-0000-4000-8000-000000000010",
        topic: "TCP congestion control",
        content: "Trimmed final body.",
        tags: ["networking", "tcp", "performance"],
      };
      yield {
        type: "done",
        messageId: "m1",
        content: "Got it.",
        topic: "TCP",
        coverageConfidence: 0.5,
      };
    });

    await useChatStore.getState().sendUserMessage("we are done");

    expect(snapshots[0]).toEqual({
      topic: "TCP congestion",
      tags: [],
      content: "",
      noteId: null,
    });
    expect(snapshots[1]).toEqual({
      topic: "TCP congestion",
      tags: [
        { label: "networking", reused: true },
        { label: "tcp", reused: false },
      ],
      content: "",
      noteId: null,
    });
    expect(snapshots[2]).toEqual({
      topic: "TCP congestion",
      tags: [
        { label: "networking", reused: true },
        { label: "tcp", reused: false },
      ],
      content: "Notes about TCP.",
      noteId: null,
    });
    expect(useChatStore.getState().draft).toEqual({
      topic: "TCP congestion control",
      tags: [
        { label: "networking", reused: true },
        { label: "tcp", reused: false },
        { label: "performance", reused: true },
      ],
      content: "Trimmed final body.",
      noteId: "00000000-0000-4000-8000-000000000010",
    });
  });

  it("replaces accumulated draft fields with authoritative draft_done payload", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      streamEvents([
        { type: "draft_topic", label: "Model topic", reused: false },
        { type: "draft_delta", text: "  partial draft  " },
        {
          type: "draft_done",
          noteId: "00000000-0000-4000-8000-000000000011",
          topic: "Resolved topic",
          content: "Authoritative body.",
          tags: ["alpha"],
        },
        {
          type: "done",
          messageId: "m1",
          content: "Done.",
          topic: "Session topic",
          coverageConfidence: 0,
        },
      ]),
    );

    await useChatStore.getState().sendUserMessage("we are done");

    expect(useChatStore.getState().draft).toEqual({
      topic: "Resolved topic",
      tags: [{ label: "alpha", reused: true }],
      content: "Authoritative body.",
      noteId: "00000000-0000-4000-8000-000000000011",
    });
  });

  it("clears draft when starting a new message", async () => {
    useChatStore.setState({
      draft: {
        topic: "Old topic",
        tags: [{ label: "old", reused: true }],
        content: "Old body",
        noteId: "old-note",
      },
    });

    let draftWhenSendCalled!: ReturnType<typeof useChatStore.getState>["draft"];

    vi.mocked(sendMessage).mockImplementation(() => {
      draftWhenSendCalled = useChatStore.getState().draft;
      return streamEvents([
        {
          type: "done",
          messageId: "m1",
          content: "Ok",
          topic: "Topic",
          coverageConfidence: 0,
        },
      ]);
    });

    await useChatStore.getState().sendUserMessage("Next question");

    expect(draftWhenSendCalled).toBeNull();
    expect(useChatStore.getState().draft).toBeNull();
  });

  it("clears draft when an in-band stream error is received", async () => {
    let draftBeforeError!: ReturnType<typeof useChatStore.getState>["draft"];

    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield { type: "draft_topic", label: "Partial topic", reused: false };
      yield { type: "draft_delta", text: "Partial body" };
      draftBeforeError = useChatStore.getState().draft;
      yield {
        type: "error",
        code: "session_note_already_drafted",
        detail: "Session already has a draft",
      };
    });

    await useChatStore.getState().sendUserMessage("we are done again");

    expect(draftBeforeError).toEqual({
      topic: "Partial topic",
      tags: [],
      content: "Partial body",
      noteId: null,
    });
    expect(useChatStore.getState().draft).toBeNull();
    expect(getStreamError()).toEqual({
      code: "session_note_already_drafted",
      detail: "Session already has a draft",
    });
  });
});
