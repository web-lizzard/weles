export const PANEL_CHROME_ROWS = 2; // top rule + hint line

export function panelBodyHeight(rows: number, reservedRows: number): number {
  return Math.max(1, rows - 1 - PANEL_CHROME_ROWS - reservedRows);
}

/** A selection-following window into a list, centered on the selected index. */
export function listWindow(
  selectedIndex: number,
  itemCount: number,
  windowSize: number,
): { start: number; size: number } {
  const size = Math.min(windowSize, itemCount);
  if (size <= 0) {
    return { start: 0, size: 0 };
  }
  const maxStart = Math.max(0, itemCount - size);
  const start = Math.min(
    maxStart,
    Math.max(0, selectedIndex - Math.floor(size / 2)),
  );
  return { start, size };
}
