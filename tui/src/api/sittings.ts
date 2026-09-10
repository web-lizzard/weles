const API_BASE_URL = "http://localhost:8000";

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

async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(url, init);
  const body: unknown = await response.json();
  if (!response.ok) {
    const errorBody = body as { code?: string; detail?: string };
    if (
      typeof errorBody.code === "string" &&
      typeof errorBody.detail === "string"
    ) {
      throw new SittingHttpError(
        errorBody.code,
        errorBody.detail,
        response.status,
      );
    }
    throw new Error(`Request failed: ${response.status}`);
  }
  return body;
}

export async function openSitting(): Promise<OpenedSitting | NothingDue> {
  const body = (await requestJson(`${API_BASE_URL}/review-sittings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })) as {
    kind: string;
    sitting_id?: string;
    card_id?: string;
    front?: string;
    sitting_complete?: boolean;
  };

  if (body.kind === "nothing_due") {
    return { kind: "nothing_due" };
  }

  if (body.kind !== "opened") {
    throw new Error("Unexpected open sitting response");
  }

  const { sitting_id, card_id, front, sitting_complete } = body;
  if (
    sitting_id === undefined ||
    card_id === undefined ||
    front === undefined ||
    sitting_complete === undefined
  ) {
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
  const body = (await requestJson(
    `${API_BASE_URL}/review-sittings/${sittingId}/cards/${cardId}/back`,
  )) as {
    sitting_id: string;
    card_id: string;
    front: string;
    back: string;
  };

  return {
    sittingId: body.sitting_id,
    cardId: body.card_id,
    front: body.front,
    back: body.back,
  };
}

export async function gradeCard(
  sittingId: string,
  cardId: string,
  grade: Grade,
): Promise<GradeApplied> {
  const body = (await requestJson(
    `${API_BASE_URL}/review-sittings/${sittingId}/cards/${cardId}/grade`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grade }),
    },
  )) as {
    sitting_id: string;
    sitting_complete: boolean;
    next_card_id: string | null;
    next_front: string | null;
  };

  return {
    sittingId: body.sitting_id,
    sittingComplete: body.sitting_complete,
    nextCardId: body.next_card_id,
    nextFront: body.next_front,
  };
}
