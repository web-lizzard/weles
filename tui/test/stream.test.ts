import { afterEach, describe, expect, it, vi } from "vitest";
import { type ReplyStreamEvent, sendMessage } from "../src/api/stream";

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
