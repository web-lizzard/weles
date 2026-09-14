import { Chalk } from "chalk";
import { describe, expect, it } from "vitest";
import { renderMarkdownLines, splitStableBlocks } from "../src/lib/markdown";

const chalk = new Chalk({ level: 1 });

const ANSI_ESCAPE = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, "g");

function stripAnsi(text: string): string {
  return text.replace(ANSI_ESCAPE, "");
}

describe("renderMarkdownLines", () => {
  it("returns no lines for empty input", () => {
    expect(renderMarkdownLines("", 80, chalk)).toEqual([]);
  });

  it("renders a depth-1 heading bold and underlined with no leading #, and a deeper heading bold only", () => {
    const lines = renderMarkdownLines("# Title\n\n## Section\n", 80, chalk);
    const joined = lines.join("\n");
    expect(joined).toContain(chalk.bold.underline("Title"));
    expect(joined).not.toContain("#");
    expect(joined).toContain(chalk.bold("Section"));
    expect(joined).not.toContain(chalk.bold.underline("Section"));
  });

  it("renders strong, em, del, and codespan as inline styling instead of raw markdown syntax", () => {
    const lines = renderMarkdownLines(
      "Some **bold** and *em* and ~~gone~~ and `code`.",
      80,
      chalk,
    );
    const joined = lines.join("\n");
    expect(joined).toContain(chalk.bold("bold"));
    expect(joined).toContain(chalk.italic("em"));
    expect(joined).toContain(chalk.strikethrough("gone"));
    expect(stripAnsi(joined)).not.toMatch(/\*\*|~~|`/);
    expect(stripAnsi(joined)).toContain("code");
    expect(joined).not.toBe(stripAnsi(joined));
  });

  it("renders bullet, ordered, nested, and task list items with the documented markers", () => {
    const lines = renderMarkdownLines(
      "- one\n  - nested\n- [ ] todo\n- [x] done\n\n1. first\n2. second\n",
      80,
      chalk,
    );
    const stripped = stripAnsi(lines.join("\n"));
    expect(stripped).toContain("• one");
    expect(stripped).toMatch(/ {2}• nested/);
    expect(stripped).toContain("☐ todo");
    expect(stripped).toContain("☑ done");
    expect(stripped).toContain("1. first");
    expect(stripped).toContain("2. second");
  });

  it("renders a fenced code block dim-indented with the fence markers removed, the same for an unclosed fence", () => {
    const closed = stripAnsi(
      renderMarkdownLines("```\nconst x = 1;\n```\n", 80, chalk).join("\n"),
    );
    expect(closed).not.toContain("```");
    expect(closed).toContain("const x = 1;");

    const unclosed = stripAnsi(
      renderMarkdownLines("```\nconst x = 1;\n", 80, chalk).join("\n"),
    );
    expect(unclosed).not.toContain("```");
    expect(unclosed).toContain("const x = 1;");
  });

  it("renders a blockquote with a dim │ prefix and an hr as a dim rule of columns width", () => {
    const joined = renderMarkdownLines("> quoted\n\n---\n", 10, chalk).join(
      "\n",
    );
    expect(joined).toContain(chalk.dim("│ "));
    expect(stripAnsi(joined)).toContain("quoted");
    expect(joined).toContain(chalk.dim("─".repeat(10)));
  });

  it("renders a link as its text followed by a dim URL", () => {
    const joined = renderMarkdownLines(
      "[text](http://example.com)\n",
      80,
      chalk,
    ).join("\n");
    expect(joined).toContain(chalk.dim("http://example.com"));
    const strippedJoined = stripAnsi(joined);
    expect(strippedJoined.indexOf("text")).toBeLessThan(
      strippedJoined.indexOf("http://example.com"),
    );
  });

  it("hard-wraps every rendered line to fit within the given column width", () => {
    const columns = 20;
    const lines = renderMarkdownLines(
      `${"a".repeat(5)} ${"b".repeat(60)}`,
      columns,
      chalk,
    );
    for (const line of lines) {
      expect(stripAnsi(line).length).toBeLessThanOrEqual(columns);
    }
    expect(lines.length).toBeGreaterThan(1);
  });
});

describe("splitStableBlocks", () => {
  it("always concatenates stable and pending back into the original source", () => {
    const source = "First paragraph.\n\nSecond paragraph still typing";
    const { stable, pending } = splitStableBlocks(source);
    expect(stable + pending).toBe(source);
  });

  it("treats a top-level token as stable once a blank line follows it and it is not the last token", () => {
    const source = "First paragraph.\n\nSecond paragraph still typing";
    const { stable, pending } = splitStableBlocks(source);
    expect(stable).toBe("First paragraph.\n\n");
    expect(pending).toBe("Second paragraph still typing");
  });

  it("keeps a list pending when the remaining text is a list continuation, even after a blank line", () => {
    const source = "- one\n- two\n\n- three";
    const { stable, pending } = splitStableBlocks(source);
    expect(stable).toBe("");
    expect(pending).toBe(source);
  });
});
