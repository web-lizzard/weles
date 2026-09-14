import { describe, expect, it } from "vitest";
import {
  type CaptureLayoutInput,
  clampDraftOffset,
  layoutCapture,
} from "../src/lib/captureLayout";

function lines(n: number, prefix = "line"): string[] {
  return Array.from({ length: n }, (_, i) => `${prefix}${i}`);
}

function baseInput(overrides: Partial<CaptureLayoutInput>): CaptureLayoutInput {
  return {
    rows: 24,
    chromeRows: 5,
    draftLines: null,
    draftOffset: 0,
    conversationLines: [],
    stableLineCount: 0,
    committedLineCount: 0,
    ...overrides,
  };
}

describe("layoutCapture", () => {
  it("caps the draft height at floor((rows - 1) / 2) when the draft exceeds half the screen", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        draftLines: lines(30),
        conversationLines: [],
      }),
    );
    // floor((24 - 1) / 2) = 11
    expect(result.draftWindow).not.toBeNull();
    expect(result.draftWindow?.height).toBe(11);
  });

  it("sizes the draft window to the draft length when it fits under half the screen", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        draftLines: lines(4),
        conversationLines: [],
      }),
    );
    expect(result.draftWindow?.height).toBe(4);
    expect(result.draftWindow?.lines).toEqual(lines(4));
  });

  it("has no draft window when draftLines is null", () => {
    const result = layoutCapture(baseInput({ draftLines: null }));
    expect(result.draftWindow).toBeNull();
  });

  it("clamps the draft window offset within [0, length - height]", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        draftLines: lines(30),
        draftOffset: 999,
      }),
    );
    // height = 11, length = 30 -> max offset = 19
    expect(result.draftWindow?.offset).toBe(19);
  });

  it("commits only the min of overflow and stableLineCount, never less than the input committed count", () => {
    // rows=24, chromeRows=5 -> space = 24 - 1 - 5 - 0 = 18
    // conversationLines longer than space by 5 -> overflow = 5
    const result = layoutCapture(
      baseInput({
        rows: 24,
        chromeRows: 5,
        conversationLines: lines(23),
        stableLineCount: 20,
        committedLineCount: 0,
      }),
    );
    expect(result.committedLineCount).toBe(5);
  });

  it("never reports fewer committed lines than were already committed, even if overflow shrinks", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        chromeRows: 5,
        conversationLines: lines(10),
        stableLineCount: 10,
        committedLineCount: 8,
      }),
    );
    // space = 18, conversationLines.length = 10 -> overflow = 0
    // min(overflow, stableLineCount) = 0, but committedLineCount input is 8
    expect(result.committedLineCount).toBe(8);
  });

  it("caps committed lines at stableLineCount even when overflow is larger", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        chromeRows: 5,
        conversationLines: lines(30),
        stableLineCount: 3,
        committedLineCount: 0,
      }),
    );
    // space = 18, overflow = 30 - 18 = 12, but stableLineCount = 3
    expect(result.committedLineCount).toBe(3);
  });

  it("shows the last `space` lines of the uncommitted conversation as the tail, hiding an oversized in-progress head", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        chromeRows: 5,
        conversationLines: lines(25),
        stableLineCount: 0,
        committedLineCount: 0,
      }),
    );
    // space = 18; committedLineCount stays 0 (stableLineCount 0 caps it)
    // tail = last 18 of conversationLines.slice(0) => lines[7..24]
    expect(result.conversationTail).toEqual(lines(25).slice(7));
    expect(result.conversationTail).toHaveLength(18);
  });

  it("fills the remaining space with blank filler rows while a draft is pinned and the tail does not fill the space", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        chromeRows: 5,
        draftLines: lines(2),
        conversationLines: lines(3),
        stableLineCount: 0,
        committedLineCount: 0,
      }),
    );
    // draftHeight = 2, space = 24 - 1 - 5 - 2 = 16, tail length = 3
    expect(result.fillerRows).toBe(16 - 3);
  });

  it("reports zero filler rows when no draft is pinned", () => {
    const result = layoutCapture(
      baseInput({
        rows: 24,
        chromeRows: 5,
        draftLines: null,
        conversationLines: lines(3),
      }),
    );
    expect(result.fillerRows).toBe(0);
  });

  it("keeps draftHeight + fillerRows + tail + chromeRows within rows - 1 across varied inputs", () => {
    const cases: CaptureLayoutInput[] = [
      baseInput({
        rows: 24,
        chromeRows: 5,
        draftLines: lines(30),
        conversationLines: lines(50),
        stableLineCount: 50,
      }),
      baseInput({
        rows: 40,
        chromeRows: 6,
        draftLines: lines(3),
        conversationLines: lines(2),
      }),
      baseInput({
        rows: 10,
        chromeRows: 4,
        draftLines: lines(1),
        conversationLines: [],
      }),
      baseInput({
        rows: 24,
        chromeRows: 5,
        draftLines: null,
        conversationLines: lines(100),
        stableLineCount: 100,
      }),
    ];
    for (const input of cases) {
      const result = layoutCapture(input);
      const draftHeight = result.draftWindow?.height ?? 0;
      const total =
        draftHeight +
        result.fillerRows +
        result.conversationTail.length +
        input.chromeRows;
      expect(total).toBeLessThanOrEqual(input.rows - 1);
    }
  });
});

describe("clampDraftOffset", () => {
  it("clamps a negative offset up to zero", () => {
    expect(clampDraftOffset(-5, 20, 5)).toBe(0);
  });

  it("clamps an offset beyond the max scroll down to length - height", () => {
    expect(clampDraftOffset(999, 20, 5)).toBe(15);
  });

  it("leaves an in-range offset unchanged", () => {
    expect(clampDraftOffset(7, 20, 5)).toBe(7);
  });

  it("clamps to zero when the draft fits entirely within the region height", () => {
    expect(clampDraftOffset(3, 4, 10)).toBe(0);
  });
});
