import { afterEach, describe, expect, it, vi } from "vitest";
import { listNotes } from "../src/api/notes";

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

describe("listNotes", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("maps a multi-item response from snake_case to camelCase", async () => {
    mockFetchJson([
      {
        note_id: "00000000-0000-4000-8000-000000000001",
        topic_label: "TCP handshakes",
        distillation_status: "ready",
        card_count: 3,
        last_updated_at: "2026-09-06T12:00:00Z",
      },
      {
        note_id: "00000000-0000-4000-8000-000000000002",
        topic_label: "DNS resolution",
        distillation_status: "generating",
        card_count: 0,
        last_updated_at: "2026-09-06T12:05:00Z",
      },
    ]);

    const items = await listNotes();

    expect(items).toEqual([
      {
        noteId: "00000000-0000-4000-8000-000000000001",
        topicLabel: "TCP handshakes",
        distillationStatus: "ready",
        cardCount: 3,
        lastUpdatedAt: "2026-09-06T12:00:00Z",
      },
      {
        noteId: "00000000-0000-4000-8000-000000000002",
        topicLabel: "DNS resolution",
        distillationStatus: "generating",
        cardCount: 0,
        lastUpdatedAt: "2026-09-06T12:05:00Z",
      },
    ]);
  });

  it("throws when the response is not ok", async () => {
    mockFetchJson({ detail: "boom" }, 500);

    await expect(listNotes()).rejects.toThrow("Failed to list notes");
  });
});
