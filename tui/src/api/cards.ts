export type Card = {
  cardId: string;
  front: string;
  back: string;
  anchorQuote: string;
  createdAt: string;
};

export async function listCards(_noteId: string): Promise<Card[]> {
  throw new Error("not implemented");
}
