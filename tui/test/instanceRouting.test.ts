import { afterEach, describe, expect, it, vi } from "vitest";
import { setInstanceAddress } from "../src/api/instance";
import { listNotes } from "../src/api/notes";
import { sendMessage } from "../src/api/stream";
import { parseInstanceAddress } from "../src/instance/address";

function mockFetchJson(body: unknown, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

function mockFetchWithDoneSse() {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(
        encoder.encode(
          'data: {"type":"done","message_id":"00000000-0000-4000-8000-000000000001","content":"Hi","topic":"T"}\n\n',
        ),
      );
      controller.close();
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

describe("instance API routing", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("sends listNotes requests to the configured instance address", async () => {
    setInstanceAddress(parseInstanceAddress("https://alpha.example"));
    mockFetchJson([]);

    await listNotes();

    const fetchMock = vi.mocked(globalThis.fetch);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/^https:\/\/alpha\.example\/notes/);
  });

  it("sends sendMessage requests to the configured instance address", async () => {
    setInstanceAddress(parseInstanceAddress("https://beta.example"));
    mockFetchWithDoneSse();

    for await (const _event of sendMessage("sess-42", "hello")) {
      // drain generator
    }

    const fetchMock = vi.mocked(globalThis.fetch);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://beta.example/capture-sessions/sess-42/messages");
  });

  it("routes new requests only to the address set after a switch", async () => {
    setInstanceAddress(parseInstanceAddress("https://first.example"));
    mockFetchJson([]);
    await listNotes();

    const fetchMock = vi.mocked(globalThis.fetch);
    expect(fetchMock.mock.calls[0]?.[0] as string).toMatch(
      /^https:\/\/first\.example/,
    );

    fetchMock.mockClear();
    setInstanceAddress(parseInstanceAddress("https://second.example"));
    await listNotes();

    expect(fetchMock).toHaveBeenCalledOnce();
    const switchedUrl = fetchMock.mock.calls[0]?.[0] as string;
    expect(switchedUrl).toMatch(/^https:\/\/second\.example/);
    expect(switchedUrl).not.toMatch(/first\.example/);
  });
});
