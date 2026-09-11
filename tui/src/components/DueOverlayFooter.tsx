import { Box, Text } from "ink";
import type { JSX } from "react";
import type { DuePartition } from "../api/due.js";
import {
  dueBreakdownEntries,
  duePartitionShowsBreakdown,
  formatDueLine,
  OVERLAY_DUE_TOTAL_HINT,
} from "../lib/dueFormat.js";

type DueOverlayFooterProps = {
  partition: DuePartition | null;
  outstandingCount: number;
  isStale: boolean;
  showToggleHint: boolean;
  toggleHint: string;
  showRejectHint?: boolean;
  rejectHint?: string;
};

export default function DueOverlayFooter({
  partition,
  outstandingCount,
  isStale,
  showToggleHint,
  toggleHint,
  showRejectHint = false,
  rejectHint,
}: DueOverlayFooterProps): JSX.Element {
  const showBreakdown =
    partition !== null && duePartitionShowsBreakdown(partition);

  return (
    <Box flexDirection="column" marginTop={1}>
      <Box flexDirection="column">
        {partition !== null ? (
          <>
            <Text color="cyan" dimColor={isStale}>
              {formatDueLine(partition.total)}
            </Text>
            {showBreakdown ? (
              dueBreakdownEntries(partition).map((entry) => (
                <Text key={entry.key}>
                  <Text color="cyan" dimColor={isStale}>
                    {entry.count}
                  </Text>
                  <Text dimColor> {entry.description}</Text>
                </Text>
              ))
            ) : (
              <Text dimColor>{OVERLAY_DUE_TOTAL_HINT}</Text>
            )}
          </>
        ) : (
          <Text dimColor>{outstandingCount} left</Text>
        )}
      </Box>
      {showToggleHint && (
        <Box marginTop={1}>
          <Text color="yellow">{toggleHint}</Text>
        </Box>
      )}
      {showRejectHint && rejectHint !== undefined && (
        <Box marginTop={showToggleHint ? 0 : 1}>
          <Text color="yellow">{rejectHint}</Text>
        </Box>
      )}
    </Box>
  );
}
