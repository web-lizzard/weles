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

export async function openSitting(): Promise<OpenedSitting | NothingDue> {
  throw new Error("openSitting not implemented");
}

export async function revealBack(
  sittingId: string,
  cardId: string,
): Promise<RevealedCard> {
  throw new Error("revealBack not implemented");
}

export async function gradeCard(
  sittingId: string,
  cardId: string,
  grade: Grade,
): Promise<GradeApplied> {
  throw new Error("gradeCard not implemented");
}
