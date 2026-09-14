import { render } from "ink-testing-library";
import { afterEach, describe, expect, it, vi } from "vitest";
import ActivityIndicator from "../src/components/ActivityIndicator";
import {
  formatElapsed,
  INDICATOR_GLYPHS,
  INDICATOR_VERBS,
  indicatorVerb,
  VERB_INTERVAL_MS,
} from "../src/lib/activityIndicator";

describe("ActivityIndicator", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("indicatorVerb returns the first verb before the first interval elapses", () => {
    expect(indicatorVerb(0)).toBe(INDICATOR_VERBS[0]);
    expect(indicatorVerb(VERB_INTERVAL_MS - 1)).toBe(INDICATOR_VERBS[0]);
  });

  it("indicatorVerb advances to the next verb once an interval elapses", () => {
    expect(indicatorVerb(VERB_INTERVAL_MS)).toBe(INDICATOR_VERBS[1]);
  });

  it("indicatorVerb wraps back to the first verb once elapsed time cycles past every verb", () => {
    const fullCycle = VERB_INTERVAL_MS * INDICATOR_VERBS.length;

    expect(indicatorVerb(fullCycle)).toBe(INDICATOR_VERBS[0]);
  });

  it("formatElapsed formats elapsed time in whole seconds, rounding down", () => {
    expect(formatElapsed(0)).toBe("0s");
    expect(formatElapsed(999)).toBe("0s");
    expect(formatElapsed(12_000)).toBe("12s");
  });

  it("renders the glyph, verb, and elapsed seconds on a single row", () => {
    vi.useFakeTimers();
    const startedAt = Date.now();

    const { lastFrame } = render(<ActivityIndicator startedAt={startedAt} />);

    const frame = lastFrame() ?? "";
    expect(frame).toContain(INDICATOR_GLYPHS[0]);
    expect(frame).toContain(INDICATOR_VERBS[0]);
    expect(frame).toContain("(0s)");
    expect(frame.trim().split("\n")).toHaveLength(1);
  });

  it("re-reads elapsed time on each animation frame as seconds pass", async () => {
    vi.useFakeTimers();
    const startedAt = Date.now();

    const { lastFrame } = render(<ActivityIndicator startedAt={startedAt} />);
    await vi.advanceTimersByTimeAsync(5_000);

    expect(lastFrame() ?? "").toContain("(5s)");
  });

  it("cycles the verb once the verb interval elapses", async () => {
    vi.useFakeTimers();
    const startedAt = Date.now();

    const { lastFrame } = render(<ActivityIndicator startedAt={startedAt} />);
    await vi.advanceTimersByTimeAsync(VERB_INTERVAL_MS);

    expect(lastFrame() ?? "").toContain(INDICATOR_VERBS[1]);
  });
});
