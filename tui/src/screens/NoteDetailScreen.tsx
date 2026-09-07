import { Box, Text } from "ink";
import { useAppStore } from "../store/index.js";
import { useNoteDetailStore } from "../store/noteDetail.js";

export default function NoteDetailScreen() {
  useAppStore((s) => s.selectedNoteId);
  useNoteDetailStore((s) => s.note);
  useNoteDetailStore((s) => s.isLoading);

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text>Note detail placeholder</Text>
    </Box>
  );
}
