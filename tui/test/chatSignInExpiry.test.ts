import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReplyStreamEvent } from "../src/api/stream";
import {
  approveNote,
  SendMessageHttpError,
  sendMessage,
  startCaptureSession,
} from "../src/api/stream";
import { SIGN_IN_EXPIRED_DETAIL, SIGN_IN_REQUIRED } from "../src/auth/expiry";
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
    approveNote: vi.fn(),
    startCaptureSession: vi.fn(),
  };
});

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

const sessionId = "sess-1";
const initialTranscript = [
  { role: "user" as const, content: "Earlier question" },
  { role: "agent" as const, content: "Earlier reply" },
];
const initialDraft = {
  topic: "TCP congestion control",
  tags: [{ label: "networking", reused: true }],
  content: "Draft body still on screen.",
  noteId: "00000000-0000-4000-8000-000000000010",
};

describe("capture chat sign-in expiry", () => {
  beforeEach(() => {
    useChatStore.setState({
      sessionId,
      topic: "TCP congestion control",
      coverageConfidence: 0.9,
      transcript: [...initialTranscript],
      currentReply: "",
      draft: { ...initialDraft },
      isStreaming: false,
      streamError: null,
      approved: false,
    });
    vi.mocked(sendMessage).mockReset();
    vi.mocked(approveNote).mockReset();
    vi.mocked(startCaptureSession).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("keeps transcript and draft when send fails with sign_in_required", async () => {
    vi.mocked(sendMessage).mockImplementation(() =>
      failingStream(
        new SendMessageHttpError(SIGN_IN_REQUIRED, "Sign-in required", 401),
      ),
    );

    await useChatStore.getState().sendUserMessage("Another message");

    const state = useChatStore.getState();
    expect(state.sessionId).toBe(sessionId);
    expect(state.transcript).toEqual([
      ...initialTranscript,
      { role: "user", content: "Another message" },
    ]);
    expect(state.draft).toEqual(initialDraft);
    expect(getStreamError()).toEqual({
      code: SIGN_IN_REQUIRED,
      detail: SIGN_IN_EXPIRED_DETAIL,
    });
    expect(state.isStreaming).toBe(false);
  });

  it("keeps draft when sign_in_required arrives after drafting events", async () => {
    vi.mocked(sendMessage).mockImplementation(async function* () {
      yield { type: "draft_topic", label: "Fresh topic", reused: false };
      yield { type: "draft_delta", text: "Partial draft" };
      throw new SendMessageHttpError(SIGN_IN_REQUIRED, "Sign-in required", 401);
    });

    await useChatStore.getState().sendUserMessage("Continue");

    const state = useChatStore.getState();
    expect(state.draft).toEqual({
      topic: "Fresh topic",
      tags: [],
      content: "Partial draft",
      noteId: null,
    });
    expect(getStreamError()?.detail).toBe(SIGN_IN_EXPIRED_DETAIL);
  });

  it("surfaces sign_in_required from startCaptureSession after approval without clearing draft", async () => {
    vi.mocked(approveNote).mockResolvedValue({
      noteId: "00000000-0000-4000-8000-000000000010",
      topic: "TCP congestion control",
      tags: ["networking"],
    });
    vi.mocked(startCaptureSession).mockRejectedValue(
      new SendMessageHttpError(SIGN_IN_REQUIRED, "Sign-in required", 401),
    );

    await useChatStore.getState().approveDraft();

    expect(useChatStore.getState().draft).toEqual(initialDraft);
    expect(useChatStore.getState().sessionId).toBe(sessionId);
    expect(useChatStore.getState().transcript).toEqual(initialTranscript);
    expect(getStreamError()).toEqual({
      code: SIGN_IN_REQUIRED,
      detail: SIGN_IN_EXPIRED_DETAIL,
    });
  });
});
