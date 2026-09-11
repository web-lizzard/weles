import { client } from "./client.js";
import { type DuePartition, toDuePartition } from "./due.js";

export const SITTING_EXPIRED = "sitting_expired";

export type Grade = "forgot" | "hard" | "good" | "easy";

type PresentedSittingFields = {
  sittingId: string;
  cardId: string | null;
  front: string | null;
  sittingComplete: boolean;
  outstandingCount: number;
  due?: DuePartition;
};

export type OpenedSitting = PresentedSittingFields & {
  kind: "opened";
};

export type ResumedSitting = PresentedSittingFields & {
  kind: "resumed";
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
  outstandingCount: number;
  nextCardId: string | null;
  nextFront: string | null;
  due?: DuePartition;
};

export type PresentedCard = {
  sittingId: string;
  cardId: string | null;
  front: string | null;
  sittingComplete: boolean;
  outstandingCount: number;
  due?: DuePartition;
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

export async function openSitting(): Promise<
  OpenedSitting | ResumedSitting | NothingDue
> {
  const { data, error, response } = await client.POST("/review-sittings");
  if (error || !data) {
    throwOnClientError(error, response, "openSitting failed");
  }

  if (data.kind === "nothing_due") {
    return { kind: "nothing_due" };
  }

  if (data.kind !== "opened" && data.kind !== "resumed") {
    throw new Error("Unexpected open sitting response");
  }

  const { sitting_id, card_id, front, sitting_complete, outstanding_count } =
    data;
  if ((card_id == null || front == null) && !sitting_complete) {
    throw new Error("Incomplete open sitting response");
  }

  const presented = {
    sittingId: sitting_id,
    cardId: card_id,
    front,
    sittingComplete: sitting_complete,
    outstandingCount: outstanding_count,
    ...(data.due != null ? { due: toDuePartition(data.due) } : {}),
  };

  if (data.kind === "resumed") {
    return { kind: "resumed", ...presented };
  }

  return { kind: "opened", ...presented };
}

export async function revealBack(
  sittingId: string,
  cardId: string,
): Promise<RevealedCard> {
  const { data, error, response } = await client.POST(
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
    outstandingCount: data.outstanding_count,
    nextCardId: data.next_card_id,
    nextFront: data.next_front,
    ...(data.due != null ? { due: toDuePartition(data.due) } : {}),
  };
}

export async function rejectCard(
  sittingId: string,
  cardId: string,
): Promise<void> {
  const { data, error, response } = await client.POST(
    "/review-sittings/{sitting_id}/cards/{card_id}/rejection",
    {
      params: { path: { sitting_id: sittingId, card_id: cardId } },
    },
  );
  if (response.status === 204) {
    return;
  }
  if (error || !data) {
    throwOnClientError(error, response, "rejectCard failed");
  }
}

export async function currentCard(sittingId: string): Promise<PresentedCard> {
  const { data, error, response } = await client.GET(
    "/review-sittings/{sitting_id}/current-card",
    { params: { path: { sitting_id: sittingId } } },
  );
  if (error || !data) {
    throwOnClientError(error, response, "currentCard failed");
  }

  return {
    sittingId: data.sitting_id,
    cardId: data.card_id,
    front: data.front,
    sittingComplete: data.sitting_complete,
    outstandingCount: data.outstanding_count,
    ...(data.due != null ? { due: toDuePartition(data.due) } : {}),
  };
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
