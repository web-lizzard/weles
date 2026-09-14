import type { ChalkInstance } from "chalk";

export type StableSplit = { stable: string; pending: string };

export function renderMarkdownLines(
  source: string,
  columns: number,
  chalk: ChalkInstance,
): string[] {
  void source;
  void columns;
  void chalk;
  throw new Error("not implemented");
}

export function splitStableBlocks(source: string): StableSplit {
  void source;
  throw new Error("not implemented");
}
