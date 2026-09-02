import { afterEach, describe, expect, it, vi } from "vitest";
import { type ReplyStreamEvent, sendMessage } from "../src/api/stream";

function mockFetchError(
  status: number,
  body: unknown,
  options: { jsonThrows?: boolean } = {},
) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: options.jsonThrows
        ? vi.fn().mockRejectedValue(new Error("invalid json"))
        : vi.fn().mockResolvedValue(body),
    }),
  );
}

function mockFetchWithSseChunks(chunks: string[]) {
  const encoder = new TextEncoder();
  let index = 0;

  const body = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index += 1;
      } else {
        controller.close();
      }
    },
  });

  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      body,
    }),
  );
}

async function collectEvents(
  sessionId: string,
  content: string,
): Promise<ReplyStreamEvent[]> {
  const events: ReplyStreamEvent[] = [];
  for await (const event of sendMessage(sessionId, content)) {
    events.push(event);
  }
  return events;
}

describe("sendMessage SSE parser", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("yields delta and done events from an SSE response body", async () => {
    mockFetchWithSseChunks([
      'data: {"type":"delta","text":"Hel"}\n\n',
      'data: {"type":"delta","text":"lo"}\n\n',
      'data: {"type":"done","message_id":"00000000-0000-4000-8000-000000000001","content":"Hello","topic":"TCP handshakes"}\n\n',
    ]);

    const events = await collectEvents("sess-1", "How does TCP work?");

    expect(events).toEqual([
      { type: "delta", text: "Hel" },
      { type: "delta", text: "lo" },
      {
        type: "done",
        messageId: "00000000-0000-4000-8000-000000000001",
        content: "Hello",
        topic: "TCP handshakes",
      },
    ]);
  });

  it("yields error events from an SSE response body", async () => {
    mockFetchWithSseChunks([
      'data: {"type":"error","code":"capture_session_not_found","detail":"Capture session not found"}\n\n',
    ]);

    const events = await collectEvents("sess-1", "hi");

    expect(events).toEqual([
      {
        type: "error",
        code: "capture_session_not_found",
        detail: "Capture session not found",
      },
    ]);
  });

  it("throws a typed error with code and detail on a pre-stream 4xx", async () => {
    mockFetchError(404, {
      code: "capture_session_not_found",
      detail: "Capture session not found",
    });

    await expect(collectEvents("missing", "hi")).rejects.toMatchObject({
      code: "capture_session_not_found",
      detail: "Capture session not found",
      status: 404,
    });
  });

  it("throws a generic error when the pre-stream response body is not JSON", async () => {
    mockFetchError(500, null, { jsonThrows: true });

    await expect(collectEvents("sess-1", "hi")).rejects.toThrow(
      "sendMessage failed: 500",
    );
  });

  it("throws a generic error when pre-stream JSON lacks code and detail", async () => {
    mockFetchError(422, { message: "validation failed" });

    await expect(collectEvents("sess-1", "hi")).rejects.toThrow(
      "sendMessage failed: 422",
    );
  });

  it("parses draft_topic, draft_tag, draft_delta, and draft_done SSE frames", async () => {
    mockFetchWithSseChunks([
      'data: {"type":"draft_topic","label":"TCP congestion","reused":false}\n\n',
      'data: {"type":"draft_tag","label":"networking","reused":true}\n\n',
      'data: {"type":"draft_tag","label":"tcp","reused":false}\n\n',
      'data: {"type":"draft_delta","text":"Notes about "}\n\n',
      'data: {"type":"draft_delta","text":"TCP."}\n\n',
      'data: {"type":"draft_done","note_id":"00000000-0000-4000-8000-000000000010","topic":"TCP congestion control","content":"Trimmed final body.","tags":["networking","tcp"]}\n\n',
    ]);

    const events = await collectEvents("sess-1", "we are done");

    expect(events).toEqual([
      { type: "draft_topic", label: "TCP congestion", reused: false },
      { type: "draft_tag", label: "networking", reused: true },
      { type: "draft_tag", label: "tcp", reused: false },
      { type: "draft_delta", text: "Notes about " },
      { type: "draft_delta", text: "TCP." },
      {
        type: "draft_done",
        noteId: "00000000-0000-4000-8000-000000000010",
        topic: "TCP congestion control",
        content: "Trimmed final body.",
        tags: ["networking", "tcp"],
      },
    ]);
  });

  it("maps coverage_confidence to coverageConfidence on done events", async () => {
    mockFetchWithSseChunks([
      'data: {"type":"done","message_id":"00000000-0000-4000-8000-000000000003","content":"Hello","topic":"TCP handshakes","coverage_confidence":1.0}\n\n',
    ]);

    const events = await collectEvents("sess-1", "How does TCP work?");

    expect(events).toEqual([
      {
        type: "done",
        messageId: "00000000-0000-4000-8000-000000000003",
        content: "Hello",
        topic: "TCP handshakes",
        coverageConfidence: 1.0,
      },
    ]);
  });

  it("parses events when SSE lines are split across stream chunks", async () => {
    mockFetchWithSseChunks([
      'data: {"type":"delta","text":"Hel',
      'lo"}\n\ndata: {"type":"done","message_id":"00000000-0000-4000-8000-000000000002","content":"Hello","topic":"TCP"}\n\n',
    ]);

    const events = await collectEvents("sess-1", "How does TCP work?");

    expect(events).toEqual([
      { type: "delta", text: "Hello" },
      {
        type: "done",
        messageId: "00000000-0000-4000-8000-000000000002",
        content: "Hello",
        topic: "TCP",
      },
    ]);
  });
});
