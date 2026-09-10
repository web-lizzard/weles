import { afterEach, describe, expect, it, vi } from "vitest";
import { openSitting } from "../src/api/sittings";

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

describe("openSitting on a just-completed sitting with no card", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("does not raise when the backend reports sitting_complete: true with card_id/front null", async () => {
    mockFetchJson({
      kind: "opened",
      sitting_id: "00000000-0000-4000-8000-000000000001",
      card_id: null,
      front: null,
      sitting_complete: true,
    });

    await expect(openSitting()).resolves.toBeTruthy();
  });
});
