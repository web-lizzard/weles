import { create } from "zustand";
import { sendMessage, startCaptureSession } from "../api/stream.js";

export type TranscriptEntry = {
  role: "user" | "agent";
  content: string;
};

type ChatState = {
  sessionId: string | null;
  topic: string | null;
  transcript: TranscriptEntry[];
  currentReply: string;
  isStreaming: boolean;
};

type ChatActions = {
  initSession: () => Promise<void>;
  sendUserMessage: (text: string) => Promise<void>;
};

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  sessionId: null,
  topic: null,
  transcript: [],
  currentReply: "",
  isStreaming: false,
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
    }));

    try {
      for await (const event of sendMessage(sessionId, text)) {
        if (event.type === "delta") {
          set((state) => ({
            currentReply: state.currentReply + event.text,
          }));
        } else {
          set((state) => ({
            transcript: [
              ...state.transcript,
              { role: "agent", content: event.content },
            ],
            currentReply: "",
            topic: event.topic,
          }));
        }
      }
    } finally {
      set({ isStreaming: false });
    }
  },
}));
