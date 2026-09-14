export const INDICATOR_GLYPHS: readonly string[] = [
  "·",
  "✢",
  "✳",
  "✶",
  "✻",
  "✽",
];

export const INDICATOR_VERBS: readonly string[] = [
  "Pondering",
  "Distilling",
  "Weighing",
  "Musing",
  "Percolating",
  "Mulling",
];

export const VERB_INTERVAL_MS = 3000;

export function indicatorVerb(_elapsedMs: number): string {
  throw new Error("not implemented");
}

export function formatElapsed(_elapsedMs: number): string {
  throw new Error("not implemented");
}
