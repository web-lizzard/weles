import { afterEach, describe, expect, it, vi } from "vitest";
import { setInstanceAddress, setSignInProvider } from "../src/api/instance";
import { listNotes } from "../src/api/notes";
import { sendMessage } from "../src/api/stream";
import { parseInstanceAddress } from "../src/instance/address";

const TOKEN = "provider-token-value";

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

function authorizationFromFetchCall(
  call: [unknown, RequestInit?],
): string | undefined {
  const [, init] = call;
  if (init?.headers) {
    const headers = init.headers as Record<string, string>;
    return headers.Authorization ?? headers.authorization;
  }
  const [input] = call;
  if (input instanceof Request) {
    return input.headers.get("Authorization") ?? undefined;
  }
  return undefined;
}

describe("authorized API requests", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    setSignInProvider(async () => null);
  });

  it("listNotes sends Authorization Bearer from the sign-in provider", async () => {
    setInstanceAddress(parseInstanceAddress("https://alpha.example"));
    setSignInProvider(async () => TOKEN);
    mockFetchJson([]);

    await listNotes();

    const fetchMock = vi.mocked(globalThis.fetch);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(
      authorizationFromFetchCall(
        fetchMock.mock.calls[0] as [unknown, RequestInit?],
      ),
    ).toBe(`Bearer ${TOKEN}`);
  });

  it("sendMessage sends Authorization Bearer from the sign-in provider", async () => {
    setInstanceAddress(parseInstanceAddress("https://beta.example"));
    setSignInProvider(async () => TOKEN);
    mockFetchWithDoneSse();

    for await (const _event of sendMessage("sess-42", "hello")) {
      // drain generator
    }

    const fetchMock = vi.mocked(globalThis.fetch);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(
      authorizationFromFetchCall(
        fetchMock.mock.calls[0] as [unknown, RequestInit?],
      ),
    ).toBe(`Bearer ${TOKEN}`);
  });

  it("listNotes sends no Authorization header when the provider yields null", async () => {
    setInstanceAddress(parseInstanceAddress("https://alpha.example"));
    setSignInProvider(async () => null);
    mockFetchJson([]);

    await listNotes();

    const fetchMock = vi.mocked(globalThis.fetch);
    expect(
      authorizationFromFetchCall(
        fetchMock.mock.calls[0] as [unknown, RequestInit?],
      ),
    ).toBeUndefined();
  });

  it("sendMessage sends no Authorization header when the provider yields null", async () => {
    setInstanceAddress(parseInstanceAddress("https://beta.example"));
    setSignInProvider(async () => null);
    mockFetchWithDoneSse();

    for await (const _event of sendMessage("sess-42", "hello")) {
      // drain generator
    }

    const fetchMock = vi.mocked(globalThis.fetch);
    expect(
      authorizationFromFetchCall(
        fetchMock.mock.calls[0] as [unknown, RequestInit?],
      ),
    ).toBeUndefined();
  });

  it("invokes the sign-in provider on every request without caching the token", async () => {
    setInstanceAddress(parseInstanceAddress("https://alpha.example"));
    const provider = vi.fn(async () => TOKEN);
    setSignInProvider(provider);
    mockFetchJson([]);

    await listNotes();
    await listNotes();

    expect(provider).toHaveBeenCalledTimes(2);
  });
});
