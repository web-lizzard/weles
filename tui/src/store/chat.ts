import { create } from "zustand";

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

export const useChatStore = create<ChatState & ChatActions>(() => ({
  sessionId: null,
  topic: null,
  transcript: [],
  currentReply: "",
  isStreaming: false,
  initSession: async () => {
    throw new Error("Not implemented");
  },
  sendUserMessage: async (_text: string) => {
    throw new Error("Not implemented");
  },
}));
