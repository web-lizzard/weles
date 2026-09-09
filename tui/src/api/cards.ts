import { client } from "./client.js";

export type AnchorLocation = {
  blockIndex: number;
  start: number;
  end: number;
  precision: "exact" | "block";
};

export type Card = {
  cardId: string;
  front: string;
  back: string;
  anchorQuote: string;
  anchorLocation: AnchorLocation | null;
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
    anchorLocation: mapAnchorLocation(item.anchor_location),
    createdAt: item.created_at,
  }));
}

function mapAnchorLocation(
  location: {
    block_index: number;
    start: number;
    end: number;
    precision: string;
  } | null,
): AnchorLocation | null {
  if (location === null) {
    return null;
  }
  return {
    blockIndex: location.block_index,
    start: location.start,
    end: location.end,
    precision: location.precision as AnchorLocation["precision"],
  };
}
