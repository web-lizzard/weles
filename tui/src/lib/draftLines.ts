import type { ChalkInstance } from "chalk";
import type { Draft } from "../store/chat.js";
import { renderMarkdownLines } from "./markdown.js";

export function renderDraftLines(
  draft: Draft,
  columns: number,
  chalk: ChalkInstance,
): string[] {
  const width = columns > 0 ? columns : 1;
  const lines: string[] = [];

  if (draft.topic !== null) {
    lines.push(`${chalk.yellow("Topic: ")}${chalk.bold(draft.topic)}`);
  }

  if (draft.tags.length > 0) {
    lines.push(`${chalk.dim("Tags: ")}${renderTags(draft.tags, chalk)}`);
  }

  if (draft.content.length > 0) {
    lines.push(chalk.dim("─".repeat(width)));
    lines.push(...renderMarkdownLines(draft.content, width, chalk));
  }

  return lines;
}

function renderTags(
  tags: { label: string; reused: boolean }[],
  chalk: ChalkInstance,
): string {
  return tags
    .map((tag) =>
      tag.reused
        ? chalk.cyan(tag.label)
        : `${chalk.cyan(tag.label)}${chalk.dim(" (new)")}`,
    )
    .join(chalk.dim(" · "));
}
