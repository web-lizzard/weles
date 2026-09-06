import { Box, Text } from "ink";
import type { NoteListItem } from "../api/notes.js";
import { useNotesPolling } from "../hooks/useNotesPolling.js";
import { useNotesStore } from "../store/notes.js";

const NOTES_POLL_INTERVAL_MS = 3000;

export default function NoteListOverlay() {
  useNotesPolling(NOTES_POLL_INTERVAL_MS);
  const items = useNotesStore((s) => s.items);
  const isLoading = useNotesStore((s) => s.isLoading);
  const error = useNotesStore((s) => s.error);
  const now = new Date();

  return (
    <Box flexDirection="column">
      <Text bold>Notes</Text>
      {error !== null && <Text color="red">{error}</Text>}
      {items.length === 0 && isLoading && <Text>Loading...</Text>}
      {items.map((item) => {
        const badge = statusBadge(item, now);
        return (
          <Text key={item.noteId}>
            {item.topicLabel}
            {badge ? ` — ${badge}` : ""} — {item.cardCount} cards
          </Text>
        );
      })}
    </Box>
  );
}

function statusBadge(item: NoteListItem, now: Date): string {
  if (item.distillationStatus === "generating") {
    return `Generating (${formatElapsed(new Date(item.lastUpdatedAt), now)})`;
  }
  if (item.distillationStatus === "failed") {
    return "Failed";
  }
  return "";
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
