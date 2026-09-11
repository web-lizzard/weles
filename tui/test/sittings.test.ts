import { afterEach, describe, expect, it, vi } from "vitest";
import {
  currentCard,
  gradeCard,
  openSitting,
  rejectCard,
  revealBack,
  SITTING_EXPIRED,
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

  const duePartitionRaw = {
    total: 5,
    not_yet_seen: 2,
    seen_still_owed: 1,
    ripe_outside_sitting: 2,
  };

  const duePartition = {
    total: 5,
    notYetSeen: 2,
    seenStillOwed: 1,
    ripeOutsideSitting: 2,
  };

  it("maps an opened sitting from snake_case to camelCase", async () => {
    mockFetchJson({
      kind: "opened",
      sitting_id: sittingId,
      card_id: cardId,
      front: "What is a SYN?",
      sitting_complete: false,
      outstanding_count: 0,
      due: duePartitionRaw,
    });

    const result = await openSitting();

    expect(result).toEqual({
      kind: "opened",
      sittingId,
      cardId,
      front: "What is a SYN?",
      sittingComplete: false,
      outstandingCount: 0,
      due: duePartition,
    });
  });

  it("returns nothing_due when the backend reports an empty backlog", async () => {
    mockFetchJson({ kind: "nothing_due" });

    const result = await openSitting();

    expect(result).toEqual({ kind: "nothing_due" });
  });

  it("maps a resumed sitting with kind resumed and outstanding_count", async () => {
    mockFetchJson({
      kind: "resumed",
      sitting_id: sittingId,
      card_id: cardId,
      front: "What is a SYN?",
      sitting_complete: false,
      outstanding_count: 2,
    });

    const result = await openSitting();

    expect(result).toEqual({
      kind: "resumed",
      sittingId,
      cardId,
      front: "What is a SYN?",
      sittingComplete: false,
      outstandingCount: 2,
    });
  });

  it("maps outstanding_count onto openSitting when kind is opened", async () => {
    mockFetchJson({
      kind: "opened",
      sitting_id: sittingId,
      card_id: cardId,
      front: "Front",
      sitting_complete: false,
      outstanding_count: 3,
    });

    const result = await openSitting();

    expect(result).toEqual({
      kind: "opened",
      sittingId,
      cardId,
      front: "Front",
      sittingComplete: false,
      outstandingCount: 3,
    });
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

  it("maps due on gradeCard from the response body", async () => {
    mockFetchJson({
      sitting_id: sittingId,
      sitting_complete: false,
      outstanding_count: 1,
      next_card_id: cardId,
      next_front: "Next front",
      due: duePartitionRaw,
    });

    const result = await gradeCard(sittingId, cardId, "good");

    expect(result.due).toEqual(duePartition);
  });

  it("posts the grade in the request body and maps gradeCard from snake_case", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          sitting_id: sittingId,
          sitting_complete: true,
          outstanding_count: 0,
          next_card_id: null,
          next_front: null,
          due: duePartitionRaw,
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
      outstandingCount: 0,
      nextCardId: null,
      nextFront: null,
      due: duePartition,
    });
  });

  it("maps outstanding_count onto gradeCard from the response body", async () => {
    mockFetchJson({
      sitting_id: sittingId,
      sitting_complete: false,
      outstanding_count: 1,
      next_card_id: cardId,
      next_front: "Next front",
    });

    const result = await gradeCard(sittingId, cardId, "good");

    expect(result).toEqual({
      sittingId,
      sittingComplete: false,
      outstandingCount: 1,
      nextCardId: cardId,
      nextFront: "Next front",
    });
  });

  it("throws SittingHttpError with SITTING_EXPIRED on a 409 expiry body", async () => {
    mockFetchJson({ code: "sitting_expired", detail: "Sitting expired" }, 409);

    await expect(openSitting()).rejects.toSatisfy((error: unknown) => {
      expect(error).toBeInstanceOf(SittingHttpError);
      const httpError = error as SittingHttpError;
      expect(httpError.code).toBe(SITTING_EXPIRED);
      expect(httpError.status).toBe(409);
      return true;
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

  it("resolves rejectCard without a body when the server returns 204", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(rejectCard(sittingId, cardId)).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/review-sittings/${sittingId}/cards/${cardId}/rejection`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws SittingHttpError from rejectCard when the server returns a client error body", async () => {
    mockFetchJson(
      { code: "card_not_presentable", detail: "Card is not presentable" },
      409,
    );

    await expect(rejectCard(sittingId, cardId)).rejects.toSatisfy(
      (error: unknown) => {
        expect(error).toBeInstanceOf(SittingHttpError);
        const httpError = error as SittingHttpError;
        expect(httpError.code).toBe("card_not_presentable");
        expect(httpError.detail).toBe("Card is not presentable");
        expect(httpError.status).toBe(409);
        return true;
      },
    );
  });

  it("maps currentCard from snake_case to camelCase including due", async () => {
    mockFetchJson({
      sitting_id: sittingId,
      card_id: cardId,
      front: "Current front",
      sitting_complete: false,
      outstanding_count: 2,
      due: duePartitionRaw,
    });

    const result = await currentCard(sittingId);

    expect(result).toEqual({
      sittingId,
      cardId,
      front: "Current front",
      sittingComplete: false,
      outstandingCount: 2,
      due: duePartition,
    });
  });
});
