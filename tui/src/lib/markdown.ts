import type { ChalkInstance } from "chalk";
import { lexer, type MarkedToken, type Token } from "marked";
import wrapAnsi from "wrap-ansi";

export type StableSplit = { stable: string; pending: string };

export function renderMarkdownLines(
  source: string,
  columns: number,
  chalk: ChalkInstance,
): string[] {
  if (source === "") return [];
  const tokens = lexer(source) as MarkedToken[];
  const rawLines = renderBlockTokens(tokens, chalk, columns);
  const wrapped: string[] = [];
  for (const line of rawLines) {
    wrapped.push(
      ...wrapAnsi(line, columns, { hard: true, trim: false }).split("\n"),
    );
  }
  return wrapped;
}

export function splitStableBlocks(source: string): StableSplit {
  const tokens = lexer(source) as MarkedToken[];

  let raw = "";
  let stableRaw = "";
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    raw += token.raw;
    if (token.type === "space") continue;

    let next = i + 1;
    while (next < tokens.length && tokens[next].type === "space") next++;
    if (next >= tokens.length) break; // last non-space token: never stable

    let gap = "";
    for (let g = i + 1; g < next; g++) gap += tokens[g].raw;

    let stable = BLANK_LINE.test(gap);
    if (stable && token.type === "list") {
      const remainingText = source.slice(raw.length + gap.length);
      if (LIST_CONTINUATION.test(remainingText)) stable = false;
    }

    if (stable) {
      stableRaw = raw + gap;
    } else {
      break;
    }
  }

  return {
    stable: stableRaw,
    pending: source.slice(stableRaw.length),
  };
}

const BLANK_LINE = /\n[ \t]*\n/;
const LIST_CONTINUATION =
  /^(?:[ \t]|[-*+](?:[ \t]|$)|\d{1,9}(?:[.)](?:[ \t]|$))?$|\d{1,9}[.)])/;

function hasInlineTokens(
  token: MarkedToken,
): token is MarkedToken & { tokens: MarkedToken[] } {
  return "tokens" in token && Array.isArray(token.tokens);
}

function renderInlineTokens(tokens: Token[], chalk: ChalkInstance): string {
  return (tokens as MarkedToken[])
    .map((token) => renderInlineToken(token, chalk))
    .join("");
}

function renderInlineToken(token: MarkedToken, chalk: ChalkInstance): string {
  switch (token.type) {
    case "text":
    case "escape":
      return hasInlineTokens(token)
        ? renderInlineTokens(token.tokens, chalk)
        : token.text;
    case "strong":
      return chalk.bold(renderInlineTokens(token.tokens, chalk));
    case "em":
      return chalk.italic(renderInlineTokens(token.tokens, chalk));
    case "del":
      return chalk.strikethrough(renderInlineTokens(token.tokens, chalk));
    case "codespan":
      return chalk.cyan(token.text);
    case "link": {
      const text = renderInlineTokens(token.tokens, chalk);
      return `${text} ${chalk.dim(token.href)}`;
    }
    case "image":
      return renderInlineTokens(token.tokens, chalk);
    case "br":
      return "\n";
    case "html":
      return token.raw;
    default:
      return token.raw;
  }
}

function renderList(
  list: Extract<MarkedToken, { type: "list" }>,
  indent: number,
  chalk: ChalkInstance,
): string[] {
  const lines: string[] = [];
  let ordinal = typeof list.start === "number" ? list.start : 1;
  const indentStr = " ".repeat(indent);

  for (const item of list.items) {
    const marker = item.task
      ? item.checked
        ? "☑ "
        : "☐ "
      : list.ordered
        ? `${ordinal}. `
        : "• ";
    if (list.ordered) ordinal += 1;

    const itemTokens = item.tokens as MarkedToken[];
    const textTokens = itemTokens.filter(
      (t) => t.type !== "list" && t.type !== "checkbox",
    );
    const nestedLists = itemTokens.filter(
      (t): t is Extract<MarkedToken, { type: "list" }> => t.type === "list",
    );
    const textLines = renderBlockTokens(textTokens, chalk, 0);
    if (textLines.length === 0) textLines.push("");

    lines.push(indentStr + marker + textLines[0]);
    const continuationIndent = indentStr + " ".repeat(marker.length);
    for (let i = 1; i < textLines.length; i++) {
      lines.push(continuationIndent + textLines[i]);
    }

    for (const nested of nestedLists) {
      lines.push(...renderList(nested, indent + 2, chalk));
    }
  }

  return lines;
}

function renderBlock(
  token: MarkedToken,
  columns: number,
  chalk: ChalkInstance,
): string[] {
  switch (token.type) {
    case "heading": {
      const text = renderInlineTokens(token.tokens, chalk);
      return [
        token.depth === 1 ? chalk.bold.underline(text) : chalk.bold(text),
      ];
    }
    case "paragraph":
      return [renderInlineTokens(token.tokens, chalk)];
    case "text":
      return [
        hasInlineTokens(token)
          ? renderInlineTokens(token.tokens, chalk)
          : token.text,
      ];
    case "code":
      return token.text.split("\n").map((line) => chalk.dim(`  ${line}`));
    case "blockquote": {
      const inner = renderBlockTokens(
        token.tokens as MarkedToken[],
        chalk,
        columns,
      );
      return inner.map((line) => `${chalk.dim("│ ")}${line}`);
    }
    case "hr":
      return [chalk.dim("─".repeat(columns))];
    case "list":
      return renderList(token, 0, chalk);
    case "space":
      return [];
    case "html":
    case "def":
      return [token.raw];
    default:
      return [token.raw];
  }
}

function renderBlockTokens(
  tokens: Token[],
  chalk: ChalkInstance,
  columns: number,
): string[] {
  const blocks: string[][] = [];
  for (const token of tokens as MarkedToken[]) {
    if (token.type === "space") continue;
    const lines = renderBlock(token, columns, chalk);
    if (lines.length > 0) blocks.push(lines);
  }
  const result: string[] = [];
  blocks.forEach((lines, index) => {
    if (index > 0) result.push("");
    result.push(...lines);
  });
  return result;
}
