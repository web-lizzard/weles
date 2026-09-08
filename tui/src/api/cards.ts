import { client } from "./client.js";

export type Card = {
  cardId: string;
  front: string;
  back: string;
  anchorQuote: string;
  createdAt: string;
};

export async function listCards(noteId: string): Promise<Card[]> {
  const { data, error, response } = await client.GET("/notes/{note_id}/cards", {
    params: { path: { note_id: noteId } },
  });
  if (error || !data) {
    if (response.status === 404) throw new Error("Note not found");
    throw new Error("Failed to load cards");
  }
  return data.map((item) => ({
    cardId: item.card_id,
    front: item.front,
    back: item.back,
    anchorQuote: item.anchor_quote,
    createdAt: item.created_at,
  }));
}
