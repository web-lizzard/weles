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

export function layoutCapture(_input: CaptureLayoutInput): CaptureLayout {
  throw new Error("not implemented");
}

export function clampDraftOffset(
  _offset: number,
  _draftLineCount: number,
  _regionHeight: number,
): number {
  throw new Error("not implemented");
}
