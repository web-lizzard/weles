import { getClient } from "./instance.js";

export type NoteListItem = {
  noteId: string;
  topicLabel: string;
  distillationStatus: "generating" | "ready" | "failed";
  cardCount: number;
  lastUpdatedAt: string;
};

export type NoteDetailTopic = { id: string; label: string };
export type NoteDetailTag = { id: string; label: string };
export type NoteBlock = { index: number; text: string };
export type NoteDetail = {
  noteId: string;
  topic: NoteDetailTopic;
  content: string;
  blocks: NoteBlock[];
  tags: NoteDetailTag[];
  distillationStatus: "generating" | "ready" | "failed";
  approvedAt: string;
  createdAt: string;
  updatedAt: string;
};

export async function getNote(noteId: string): Promise<NoteDetail> {
  const { data, error, response } = await getClient().GET("/notes/{note_id}", {
    params: { path: { note_id: noteId } },
  });
  if (error || !data) {
    if (response.status === 404) throw new Error("Note not found");
    throw new Error("Failed to load note");
  }
  return {
    noteId: data.note_id,
    topic: { id: data.topic.id, label: data.topic.label },
    content: data.content,
    blocks: data.blocks.map((block) => ({
      index: block.index,
      text: block.text,
    })),
    tags: data.tags.map((t) => ({ id: t.id, label: t.label })),
    distillationStatus:
      data.distillation_status as NoteDetail["distillationStatus"],
    approvedAt: data.approved_at,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}

export async function listNotes(): Promise<NoteListItem[]> {
  const { data, error } = await getClient().GET("/notes");
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
