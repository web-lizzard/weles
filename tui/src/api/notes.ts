export type NoteListItem = {
  noteId: string;
  topicLabel: string;
  distillationStatus: "generating" | "ready" | "failed";
  cardCount: number;
  lastUpdatedAt: string;
};

export async function listNotes(): Promise<NoteListItem[]> {
  throw new Error("Not implemented");
}
