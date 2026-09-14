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

export function indicatorVerb(elapsedMs: number): string {
  const index =
    Math.floor(elapsedMs / VERB_INTERVAL_MS) % INDICATOR_VERBS.length;
  return INDICATOR_VERBS[index] as string;
}

export function formatElapsed(elapsedMs: number): string {
  return `${Math.floor(elapsedMs / 1000)}s`;
}
