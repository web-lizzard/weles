import { Box, Text } from "ink";
import type { NoteListItem } from "../api/notes.js";
import { useNotesPolling } from "../hooks/useNotesPolling.js";

const NOTES_POLL_INTERVAL_MS = 3000;

export default function NoteListOverlay() {
  useNotesPolling(NOTES_POLL_INTERVAL_MS);

  return (
    <Box flexDirection="column">
      <Text bold>Notes</Text>
    </Box>
  );
}

function statusBadge(_item: NoteListItem, _now: Date): string {
  throw new Error("not implemented");
}
