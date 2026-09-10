import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchDueCount } from "../src/api/due";

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

const RAW_PARTITION = {
  total: 5,
  not_yet_seen: 2,
  seen_still_owed: 1,
  ripe_outside_sitting: 2,
};

const PARTITION = {
  total: 5,
  notYetSeen: 2,
  seenStillOwed: 1,
  ripeOutsideSitting: 2,
};

describe("due API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("maps GET /due-cards/count nested due from snake_case to camelCase", async () => {
    mockFetchJson({ due: RAW_PARTITION });

    await expect(fetchDueCount()).resolves.toEqual(PARTITION);
  });
});
