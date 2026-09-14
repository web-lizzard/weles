import { create } from "zustand";
import {
  approveNote,
  SendMessageHttpError,
  sendMessage,
  startCaptureSession,
} from "../api/stream.js";
import {
  isSignInRequired,
  SIGN_IN_EXPIRED_DETAIL,
  SIGN_IN_REQUIRED,
} from "../auth/expiry.js";

export type TranscriptEntry =
  | { role: "user" | "agent"; content: string }
  | { role: "topic"; content: string };

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
  approvalReceipt: boolean;
  historyEpoch: number;
  turnStartedAt: number | null;
};

type ChatActions = {
  initSession: () => Promise<void>;
  sendUserMessage: (text: string) => Promise<void>;
  approveDraft: () => Promise<void>;
};

function signInRequiredStreamError(): StreamError {
  return { code: SIGN_IN_REQUIRED, detail: SIGN_IN_EXPIRED_DETAIL };
}

function streamErrorFromSendMessageHttpError(
  error: SendMessageHttpError,
): StreamError {
  if (isSignInRequired(error.code)) {
    return signInRequiredStreamError();
  }
  return { code: error.code, detail: error.detail };
}

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
  approvalReceipt: false,
  historyEpoch: 0,
  turnStartedAt: null,
  initSession: async () => {
    const { sessionId } = await startCaptureSession();
    set({ sessionId });
  },
  sendUserMessage: async (text: string) => {
    const { sessionId, draft: draftBeforeSend } = get();
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
          if (isSignInRequired(event.code)) {
            set({ streamError: signInRequiredStreamError() });
          } else {
            set({
              streamError: { code: event.code, detail: event.detail },
              draft: null,
            });
          }
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
        if (isSignInRequired(error.code)) {
          set((state) => ({
            streamError: signInRequiredStreamError(),
            ...(state.draft === null ? { draft: draftBeforeSend } : {}),
          }));
        } else {
          set({
            streamError: streamErrorFromSendMessageHttpError(error),
            draft: null,
          });
        }
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
    const { sessionId, draft } = get();
    if (!draft?.noteId) {
      set({
        streamError: {
          code: "no_draft_to_approve",
          detail: "There is no draft ready to approve yet.",
        },
      });
      return;
    }
    if (!sessionId) {
      throw new Error("No active session");
    }

    try {
      await approveNote(sessionId);
      const { sessionId: newSessionId } = await startCaptureSession();
      set({
        approvalReceipt: true,
        approved: false,
        topic: null,
        draft: null,
        transcript: [],
        currentReply: "",
        coverageConfidence: null,
        streamError: null,
        sessionId: newSessionId,
      });
    } catch (error) {
      if (error instanceof SendMessageHttpError) {
        set({ streamError: streamErrorFromSendMessageHttpError(error) });
      } else {
        const message = error instanceof Error ? error.message : String(error);
        set({ streamError: { code: "unknown_error", detail: message } });
      }
    }
  },
}));
