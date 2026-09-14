import type { ChalkInstance } from "chalk";
import type { TranscriptEntry } from "../store/chat.js";

export type ConversationLines = { lines: string[]; stableLineCount: number };

export function renderConversationLines(_input: {
  showBrand: boolean; // true in epoch 0
  showReceipt: boolean; // approvalReceipt
  transcript: TranscriptEntry[];
  currentReply: string;
  columns: number;
  chalk: ChalkInstance;
}): ConversationLines {
  throw new Error("not implemented");
}
