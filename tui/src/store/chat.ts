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

type StreamError = { code: string; detail: string } | null;

type ChatState = {
  sessionId: string | null;
  topic: string | null;
  coverageConfidence: number | null;
  transcript: TranscriptEntry[];
  currentReply: string;
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
    }));

    try {
      for await (const event of sendMessage(sessionId, text)) {
        if (event.type === "delta") {
          set((state) => ({
            currentReply: state.currentReply + event.text,
          }));
        } else if (event.type === "error") {
          set({ streamError: { code: event.code, detail: event.detail } });
          break;
        } else {
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
        set({ streamError: { code: error.code, detail: error.detail } });
      } else {
        const message = error instanceof Error ? error.message : String(error);
        set({ streamError: { code: "unknown_error", detail: message } });
      }
    } finally {
      set({ isStreaming: false });
    }
  },
}));
