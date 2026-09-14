import type { ChalkInstance } from "chalk";
import wrapAnsi from "wrap-ansi";
import type { TranscriptEntry } from "../store/chat.js";
import { renderMarkdownLines, splitStableBlocks } from "./markdown.js";

export type ConversationLines = { lines: string[]; stableLineCount: number };

const WELES_TAGLINE = "wisdom through questions";
const AGENT_LABEL = "🦉 Weles: ";
const USER_LABEL = "🧑 You: ";
const APPROVED_RECEIPT_TEXT = "✓ Approved — queued for saving";

export function renderConversationLines(input: {
  showBrand: boolean; // true in epoch 0
  showReceipt: boolean; // approvalReceipt
  transcript: TranscriptEntry[];
  currentReply: string;
  columns: number;
  chalk: ChalkInstance;
}): ConversationLines {
  const { showBrand, showReceipt, transcript, currentReply, chalk } = input;
  const columns = input.columns > 0 ? input.columns : 1;

  const lines: string[] = [];

  if (showBrand) {
    lines.push(
      ...wrapLine(`${chalk.yellow("Weles:")} ${WELES_TAGLINE}`, columns),
    );
    lines.push(chalk.dim("─".repeat(columns)));
  }

  if (showReceipt) {
    lines.push("═".repeat(columns));
    lines.push(chalk.green(APPROVED_RECEIPT_TEXT));
  }

  for (const entry of transcript) {
    lines.push(...renderTranscriptEntryLines(entry, columns, chalk));
  }

  let stableLineCount = lines.length;

  if (currentReply.length > 0) {
    const { stable, pending } = splitStableBlocks(currentReply);
    const stableLines =
      stable.length > 0 ? renderMarkdownLines(stable, columns, chalk) : [];
    const pendingLines =
      pending.length > 0 ? renderMarkdownLines(pending, columns, chalk) : [];
    const replyLines = [...stableLines, ...pendingLines];
    if (replyLines.length === 0) {
      replyLines.push("");
    }
    replyLines[0] = prefixAgentLabel(replyLines[0] as string, chalk);
    lines.push(...replyLines);
    stableLineCount += stableLines.length;
  }

  return { lines, stableLineCount };
}

function renderTranscriptEntryLines(
  entry: TranscriptEntry,
  columns: number,
  chalk: ChalkInstance,
): string[] {
  if (entry.role === "user") {
    return wrapLine(`${USER_LABEL}${entry.content}`, columns);
  }
  if (entry.role === "topic") {
    return wrapLine(chalk.bold(`Topic: ${entry.content}`), columns);
  }

  const bodyLines = renderMarkdownLines(entry.content, columns, chalk);
  const lines = bodyLines.length > 0 ? bodyLines : [""];
  lines[0] = prefixAgentLabel(lines[0] as string, chalk);
  return lines;
}

function prefixAgentLabel(firstLine: string, chalk: ChalkInstance): string {
  return `${chalk.yellow(AGENT_LABEL)}${firstLine}`;
}

function wrapLine(text: string, columns: number): string[] {
  return wrapAnsi(text, columns, { hard: true, trim: false }).split("\n");
}
