import { Box, Text } from "ink";
import type { JSX } from "react";
import { formatDueLine } from "../lib/dueFormat.js";
import { useDueStore } from "../store/due.js";
import { useAppStore } from "../store/index.js";

const APPROVE_HINT_TEXT = "/approve to save this note";

type StatusLineProps = {
  columns: number;
  showApproveHint: boolean;
};

export default function StatusLine({
  columns,
  showApproveHint,
}: StatusLineProps): JSX.Element {
  const partition = useDueStore((state) => state.partition);
  const isStale = useDueStore((state) => state.isStale);
  const isSittingOverlayOpen = useAppStore(
    (state) => state.isSittingOverlayOpen,
  );
  const showDueCount = partition !== null && !isSittingOverlayOpen;

  return (
    <Box
      width={columns > 0 ? columns : undefined}
      justifyContent="space-between"
    >
      <Text color="yellow" dimColor={isStale}>
        {showDueCount ? formatDueLine(partition.total) : ""}
      </Text>
      {showApproveHint && <Text dimColor>{APPROVE_HINT_TEXT}</Text>}
    </Box>
  );
}
