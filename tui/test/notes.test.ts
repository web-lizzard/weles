import { afterEach, describe, expect, it, vi } from "vitest";
import { getNote, listNotes } from "../src/api/notes";

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

describe("getNote", () => {
  const noteId = "00000000-0000-4000-8000-000000000001";

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("maps a full detail response from snake_case to camelCase", async () => {
    mockFetchJson({
      note_id: noteId,
      topic: {
        id: "00000000-0000-4000-8000-000000000010",
        label: "TCP handshakes",
      },
      content: "We discussed how connections are established.",
      tags: [
        { id: "00000000-0000-4000-8000-000000000021", label: "networking" },
        { id: "00000000-0000-4000-8000-000000000022", label: "tcp" },
      ],
      distillation_status: "ready",
      approved_at: "2026-09-06T12:00:00Z",
      created_at: "2026-09-06T11:00:00Z",
      updated_at: "2026-09-06T12:00:00Z",
    });

    const note = await getNote(noteId);

    expect(note).toEqual({
      noteId,
      topic: {
        id: "00000000-0000-4000-8000-000000000010",
        label: "TCP handshakes",
      },
      content: "We discussed how connections are established.",
      tags: [
        { id: "00000000-0000-4000-8000-000000000021", label: "networking" },
        { id: "00000000-0000-4000-8000-000000000022", label: "tcp" },
      ],
      distillationStatus: "ready",
      approvedAt: "2026-09-06T12:00:00Z",
      createdAt: "2026-09-06T11:00:00Z",
      updatedAt: "2026-09-06T12:00:00Z",
    });
  });

  it("throws with a distinct message when the note is not found", async () => {
    mockFetchJson(
      { code: "distill_note_not_found", detail: "Note not found" },
      404,
    );

    await expect(getNote(noteId)).rejects.toThrow("Note not found");
  });

  it("throws with a generic message when the response is not ok", async () => {
    mockFetchJson({ detail: "boom" }, 500);

    await expect(getNote(noteId)).rejects.toThrow("Failed to load note");
  });
});
