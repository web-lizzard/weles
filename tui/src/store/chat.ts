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
};

type ChatActions = {
  initSession: () => Promise<void>;
  sendUserMessage: (text: string) => Promise<void>;
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
          set((state) => ({
            draft: state.draft
              ? { ...state.draft, tags: [...state.draft.tags, event.label] }
              : {
                  topic: null,
                  tags: [event.label],
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
          set({
            draft: {
              topic: event.topic,
              tags: event.tags,
              content: event.content,
              noteId: event.noteId,
            },
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
}));
