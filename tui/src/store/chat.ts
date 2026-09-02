import { create } from "zustand";
import {
  SendMessageHttpError,
  sendMessage,
  startCaptureSession,
} from "../api/stream.js";

export type TranscriptEntry = {
  role: "user" | "agent";
  content: string;
};

export type Draft = {
  topic: string | null;
  tags: { label: string; reused: boolean }[];
  content: string;
  noteId: string | null;
};

type StreamError = { code: string; detail: string } | null;

type ChatState = {
  sessionId: string | null;
  topic: string | null;
  coverageConfidence: number | null;
  transcript: TranscriptEntry[];
  currentReply: string;
  draft: Draft | null;
  isStreaming: boolean;
  streamError: StreamError;
  approved: boolean;
};

type ChatActions = {
  initSession: () => Promise<void>;
  sendUserMessage: (text: string) => Promise<void>;
  approveDraft: () => Promise<void>;
};

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  sessionId: null,
  topic: null,
  coverageConfidence: null,
  transcript: [],
  currentReply: "",
  draft: null,
  isStreaming: false,
  streamError: null,
  approved: false,
  initSession: async () => {
    const { sessionId } = await startCaptureSession();
    set({ sessionId });
  },
  sendUserMessage: async (text: string) => {
    const { sessionId } = get();
    if (!sessionId) {
      throw new Error("No active session");
    }

    set((state) => ({
      transcript: [...state.transcript, { role: "user", content: text }],
      isStreaming: true,
      streamError: null,
      draft: null,
    }));

    try {
      for await (const event of sendMessage(sessionId, text)) {
        if (event.type === "delta") {
          set((state) => ({
            currentReply: state.currentReply + event.text,
          }));
        } else if (event.type === "error") {
          set({
            streamError: { code: event.code, detail: event.detail },
            draft: null,
          });
          break;
        } else if (event.type === "draft_topic") {
          set({
            draft: {
              topic: event.label,
              tags: [],
              content: "",
              noteId: null,
            },
          });
        } else if (event.type === "draft_tag") {
          const tag = { label: event.label, reused: event.reused };
          set((state) => ({
            draft: state.draft
              ? { ...state.draft, tags: [...state.draft.tags, tag] }
              : {
                  topic: null,
                  tags: [tag],
                  content: "",
                  noteId: null,
                },
          }));
        } else if (event.type === "draft_delta") {
          set((state) => ({
            draft: state.draft
              ? { ...state.draft, content: state.draft.content + event.text }
              : {
                  topic: null,
                  tags: [],
                  content: event.text,
                  noteId: null,
                },
          }));
        } else if (event.type === "draft_done") {
          set((state) => {
            const seen = new Map(
              (state.draft?.tags ?? []).map((tag) => [tag.label, tag.reused]),
            );
            return {
              draft: {
                topic: event.topic,
                tags: event.tags.map((label) => ({
                  label,
                  reused: seen.get(label) ?? true,
                })),
                content: event.content,
                noteId: event.noteId,
              },
            };
          });
        } else if (event.type === "done") {
          set((state) => ({
            transcript: [
              ...state.transcript,
              { role: "agent", content: event.content },
            ],
            currentReply: "",
            topic: event.topic,
            coverageConfidence: event.coverageConfidence,
          }));
        }
      }
    } catch (error) {
      if (error instanceof SendMessageHttpError) {
        set({
          streamError: { code: error.code, detail: error.detail },
          draft: null,
        });
      } else {
        const message = error instanceof Error ? error.message : String(error);
        set({
          streamError: { code: "unknown_error", detail: message },
          draft: null,
        });
      }
    } finally {
      set({ isStreaming: false });
    }
  },
  approveDraft: async () => {
    throw new Error("Not implemented");
  },
}));
