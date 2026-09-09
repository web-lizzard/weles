import { afterEach, describe, expect, it, vi } from "vitest";
import { listCards } from "../src/api/cards";

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

describe("listCards", () => {
  const noteId = "00000000-0000-4000-8000-000000000001";

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("maps every card field from snake_case to camelCase", async () => {
    mockFetchJson([
      {
        card_id: "00000000-0000-4000-8000-000000000101",
        front: "What is a SYN?",
        back: "The first packet of a TCP handshake.",
        anchor_quote: "The client sends SYN",
        anchor_location: {
          block_index: 0,
          start: 4,
          end: 21,
          precision: "exact",
        },
        created_at: "2026-09-06T12:00:00Z",
      },
    ]);

    const cards = await listCards(noteId);

    expect(cards).toEqual([
      {
        cardId: "00000000-0000-4000-8000-000000000101",
        front: "What is a SYN?",
        back: "The first packet of a TCP handshake.",
        anchorQuote: "The client sends SYN",
        anchorLocation: {
          blockIndex: 0,
          start: 4,
          end: 21,
          precision: "exact",
        },
        createdAt: "2026-09-06T12:00:00Z",
      },
    ]);
  });

  it("throws with a distinct message when the note is not found", async () => {
    mockFetchJson(
      { code: "distill_note_not_found", detail: "Note not found" },
      404,
    );

    await expect(listCards(noteId)).rejects.toThrow("Note not found");
  });

  it("throws with a generic message when the response is not ok", async () => {
    mockFetchJson({ detail: "boom" }, 500);

    await expect(listCards(noteId)).rejects.toThrow("Failed to load cards");
  });
});
