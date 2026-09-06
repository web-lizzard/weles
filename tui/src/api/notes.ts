import { client } from "./client.js";

export type NoteListItem = {
  noteId: string;
  topicLabel: string;
  distillationStatus: "generating" | "ready" | "failed";
  cardCount: number;
  lastUpdatedAt: string;
};

export async function listNotes(): Promise<NoteListItem[]> {
  const { data, error } = await client.GET("/notes");
  if (error || !data) {
    throw new Error("Failed to list notes");
  }
  return data.map((item) => ({
    noteId: item.note_id,
    topicLabel: item.topic_label,
    distillationStatus:
      item.distillation_status as NoteListItem["distillationStatus"],
    cardCount: item.card_count,
    lastUpdatedAt: item.last_updated_at,
  }));
}
