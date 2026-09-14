import type { ChalkInstance } from "chalk";
import type { Draft } from "../store/chat.js";

export function renderDraftLines(
  _draft: Draft,
  _columns: number,
  _chalk: ChalkInstance,
): string[] {
  throw new Error("not implemented");
}
