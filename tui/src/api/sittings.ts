import { client } from "./client.js";

export type Grade = "forgot" | "hard" | "good" | "easy";

export type OpenedSitting = {
  kind: "opened";
  sittingId: string;
  cardId: string;
  front: string;
  sittingComplete: boolean;
};

export type NothingDue = { kind: "nothing_due" };

export type RevealedCard = {
  sittingId: string;
  cardId: string;
  front: string;
  back: string;
};

export type GradeApplied = {
  sittingId: string;
  sittingComplete: boolean;
  nextCardId: string | null;
  nextFront: string | null;
};

export class SittingHttpError extends Error {
  constructor(
    public code: string,
    public detail: string,
    public status: number,
  ) {
    super(detail);
  }
}

function throwOnClientError(
  error: unknown,
  response: Response,
  fallbackMessage: string,
): never {
  const body = error as { code?: string; detail?: string } | undefined;
  if (
    body &&
    typeof body.code === "string" &&
    typeof body.detail === "string"
  ) {
    throw new SittingHttpError(body.code, body.detail, response.status);
  }
  throw new Error(`${fallbackMessage}: ${response.status}`);
}

export async function openSitting(): Promise<OpenedSitting | NothingDue> {
  const { data, error, response } = await client.POST("/review-sittings");
  if (error || !data) {
    throwOnClientError(error, response, "openSitting failed");
  }

  if (data.kind === "nothing_due") {
    return { kind: "nothing_due" };
  }

  if (data.kind !== "opened") {
    throw new Error("Unexpected open sitting response");
  }

  const { sitting_id, card_id, front, sitting_complete } = data;
  if (card_id == null || front == null) {
    throw new Error("Incomplete opened sitting response");
  }

  return {
    kind: "opened",
    sittingId: sitting_id,
    cardId: card_id,
    front,
    sittingComplete: sitting_complete,
  };
}

export async function revealBack(
  sittingId: string,
  cardId: string,
): Promise<RevealedCard> {
  const { data, error, response } = await client.GET(
    "/review-sittings/{sitting_id}/cards/{card_id}/back",
    { params: { path: { sitting_id: sittingId, card_id: cardId } } },
  );
  if (error || !data) {
    throwOnClientError(error, response, "revealBack failed");
  }

  return {
    sittingId: data.sitting_id,
    cardId: data.card_id,
    front: data.front,
    back: data.back,
  };
}

export async function gradeCard(
  sittingId: string,
  cardId: string,
  grade: Grade,
): Promise<GradeApplied> {
  const { data, error, response } = await client.POST(
    "/review-sittings/{sitting_id}/cards/{card_id}/grade",
    {
      params: { path: { sitting_id: sittingId, card_id: cardId } },
      body: { grade },
    },
  );
  if (error || !data) {
    throwOnClientError(error, response, "gradeCard failed");
  }

  return {
    sittingId: data.sitting_id,
    sittingComplete: data.sitting_complete,
    nextCardId: data.next_card_id,
    nextFront: data.next_front,
  };
}
