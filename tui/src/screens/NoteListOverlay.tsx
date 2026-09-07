import { Box, Text, useInput, useStdout } from "ink";
import type { NoteListItem } from "../api/notes.js";
import { useNotesPolling } from "../hooks/useNotesPolling.js";
import { useAppStore } from "../store/index.js";
import { useNotesStore } from "../store/notes.js";

const NOTES_POLL_INTERVAL_MS = 3000;
const DEFAULT_TERMINAL_COLUMNS = 80;

export default function NoteListOverlay() {
  useNotesPolling(NOTES_POLL_INTERVAL_MS);
  const items = useNotesStore((s) => s.items);
  const isLoading = useNotesStore((s) => s.isLoading);
  const error = useNotesStore((s) => s.error);
  const selectedIndex = useAppStore((s) => s.selectedIndex);
  const setSelectedIndex = useAppStore((s) => s.setSelectedIndex);
  const openDetail = useAppStore((s) => s.openDetail);
  const now = new Date();
  const effectiveIndex =
    items.length === 0 ? 0 : Math.min(selectedIndex, items.length - 1);

  useInput((_input, key) => {
    if (items.length === 0) {
      return;
    }

    if (key.upArrow) {
      setSelectedIndex(clamp(selectedIndex - 1, 0, items.length - 1));
      return;
    }

    if (key.downArrow) {
      setSelectedIndex(clamp(selectedIndex + 1, 0, items.length - 1));
      return;
    }

    if (key.return) {
      const item = items[effectiveIndex];
      if (item.distillationStatus === "ready") {
        openDetail(item.noteId);
      }
    }
  });

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text dimColor>← ESC to go back</Text>
      <Box marginTop={1} flexDirection="column" gap={1} flexGrow={1}>
        {error !== null && <Text color="red">{error}</Text>}
        <Text bold>Notes</Text>
        {items.length === 0 && isLoading && <Text>Loading...</Text>}
        <Box flexDirection="column" gap={1}>
          {items.map((item, index) => (
            <NoteRow
              key={item.noteId}
              item={item}
              now={now}
              isSelected={index === effectiveIndex}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function NoteRow({
  item,
  now,
  isSelected,
}: {
  item: NoteListItem;
  now: Date;
  isSelected: boolean;
}) {
  const { stdout } = useStdout();
  const columns =
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS;
  // Overlay shell padding (1 each side) + bullet column.
  const contentWidth = Math.max(1, columns - 4);

  return (
    <Box flexDirection="row" alignItems="flex-start">
      <Text dimColor>• </Text>
      <Box flexDirection="column" width={contentWidth}>
        <Text wrap="wrap" color={isSelected ? "blue" : undefined}>
          {item.topicLabel}
        </Text>
        <Box flexDirection="row" gap={1} alignItems="center">
          <StatusBadge item={item} now={now} />
          <Text dimColor>
            {item.cardCount} {item.cardCount === 1 ? "card" : "cards"}
          </Text>
        </Box>
      </Box>
    </Box>
  );
}

function StatusBadge({ item, now }: { item: NoteListItem; now: Date }) {
  if (item.distillationStatus === "ready") {
    return null;
  }

  const label =
    item.distillationStatus === "generating"
      ? `Generating (${formatElapsed(new Date(item.lastUpdatedAt), now)})`
      : "Failed";
  const color = item.distillationStatus === "generating" ? "yellow" : "red";

  return (
    <Box borderStyle="round" borderColor={color} paddingX={1}>
      <Text color={color}>{label}</Text>
    </Box>
  );
}

function formatElapsed(from: Date, now: Date): string {
  const seconds = Math.max(
    0,
    Math.floor((now.getTime() - from.getTime()) / 1000),
  );
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}
