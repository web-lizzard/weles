import { afterEach, describe, expect, it, vi } from "vitest";
import { delegatedFetch } from "../src/api/client";

describe("delegatedFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("forwards a plain url and init to global fetch", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await delegatedFetch("http://localhost:8000/health", { method: "GET" });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/health", {
      method: "GET",
    });
  });

  it("unwraps an openapi-fetch Request into url, method, headers, and body", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const request = new Request(
      "http://localhost:8000/review-sittings/s1/cards/c1/grade",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ grade: "good" }),
      },
    );

    await delegatedFetch(request);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/review-sittings/s1/cards/c1/grade");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(init.body).toBe(JSON.stringify({ grade: "good" }));
  });
});
