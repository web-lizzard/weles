export type CaptureLayoutInput = {
  rows: number; // terminal rows; live region budget is rows - 1
  chromeRows: number; // indicator + transient messages + frame (3) + status line
  draftLines: string[] | null; // null when no draft exists
  draftOffset: number;
  conversationLines: string[]; // all lines of the current epoch, oldest first
  stableLineCount: number; // prefix of conversationLines eligible for history
  committedLineCount: number; // lines already emitted to <Static>
};

export type CaptureLayout = {
  committedLineCount: number; // never less than the input value
  draftWindow: {
    lines: string[];
    offset: number;
    height: number;
    moreAbove: boolean;
    moreBelow: boolean;
  } | null;
  conversationTail: string[];
  fillerRows: number; // blank rows between tail and chrome while a draft is pinned
};

export function layoutCapture(input: CaptureLayoutInput): CaptureLayout {
  const {
    rows,
    chromeRows,
    draftLines,
    draftOffset,
    conversationLines,
    stableLineCount,
    committedLineCount,
  } = input;

  const draftCap = Math.floor((rows - 1) / 2);
  const draftHeight =
    draftLines === null ? 0 : Math.min(draftLines.length, draftCap);

  const draftWindow =
    draftLines === null
      ? null
      : (() => {
          const offset = clampDraftOffset(
            draftOffset,
            draftLines.length,
            draftHeight,
          );
          return {
            lines: draftLines.slice(offset, offset + draftHeight),
            offset,
            height: draftHeight,
            moreAbove: offset > 0,
            moreBelow: offset + draftHeight < draftLines.length,
          };
        })();

  const space = Math.max(0, rows - 1 - chromeRows - draftHeight);
  const overflow = Math.max(0, conversationLines.length - space);
  const newCommittedLineCount = Math.max(
    committedLineCount,
    Math.min(overflow, stableLineCount),
  );

  const remaining = conversationLines.slice(newCommittedLineCount);
  const conversationTail = remaining.slice(
    Math.max(0, remaining.length - space),
  );

  const fillerRows = draftLines === null ? 0 : space - conversationTail.length;

  return {
    committedLineCount: newCommittedLineCount,
    draftWindow,
    conversationTail,
    fillerRows,
  };
}

export function clampDraftOffset(
  offset: number,
  draftLineCount: number,
  regionHeight: number,
): number {
  const maxOffset = Math.max(0, draftLineCount - regionHeight);
  return Math.min(Math.max(offset, 0), maxOffset);
}
