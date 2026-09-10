import { afterEach, describe, expect, it, vi } from "vitest";
import {
  gradeCard,
  openSitting,
  revealBack,
  SittingHttpError,
} from "../src/api/sittings";

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

describe("sittings API", () => {
  const sittingId = "00000000-0000-4000-8000-000000000001";
  const cardId = "00000000-0000-4000-8000-000000000101";

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("maps an opened sitting from snake_case to camelCase", async () => {
    mockFetchJson({
      kind: "opened",
      sitting_id: sittingId,
      card_id: cardId,
      front: "What is a SYN?",
      sitting_complete: false,
    });

    const result = await openSitting();

    expect(result).toEqual({
      kind: "opened",
      sittingId,
      cardId,
      front: "What is a SYN?",
      sittingComplete: false,
    });
  });

  it("returns nothing_due when the backend reports an empty backlog", async () => {
    mockFetchJson({ kind: "nothing_due" });

    const result = await openSitting();

    expect(result).toEqual({ kind: "nothing_due" });
  });

  it("maps revealBack fields from snake_case to camelCase", async () => {
    mockFetchJson({
      sitting_id: sittingId,
      card_id: cardId,
      front: "Front text",
      back: "Back text",
    });

    const result = await revealBack(sittingId, cardId);

    expect(result).toEqual({
      sittingId,
      cardId,
      front: "Front text",
      back: "Back text",
    });
  });

  it("posts the grade in the request body and maps gradeCard from snake_case", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          sitting_id: sittingId,
          sitting_complete: true,
          next_card_id: null,
          next_front: null,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await gradeCard(sittingId, cardId, "good");

    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/review-sittings/${sittingId}/cards/${cardId}/grade`,
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grade: "good" }),
      }),
    );
    expect(result).toEqual({
      sittingId,
      sittingComplete: true,
      nextCardId: null,
      nextFront: null,
    });
  });

  it("throws SittingHttpError when the response body carries code and detail", async () => {
    mockFetchJson(
      { code: "sitting_not_found", detail: "Sitting not found" },
      404,
    );

    await expect(openSitting()).rejects.toSatisfy((error: unknown) => {
      expect(error).toBeInstanceOf(SittingHttpError);
      const httpError = error as SittingHttpError;
      expect(httpError.code).toBe("sitting_not_found");
      expect(httpError.detail).toBe("Sitting not found");
      expect(httpError.status).toBe(404);
      expect(httpError.message).toBe("Sitting not found");
      return true;
    });
  });
});
