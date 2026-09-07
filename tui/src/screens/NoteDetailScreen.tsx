import { Box, Text } from "ink";
import { useEffect } from "react";
import { useAppStore } from "../store/index.js";
import { useNoteDetailStore } from "../store/noteDetail.js";

export default function NoteDetailScreen() {
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const note = useNoteDetailStore((s) => s.note);
  const isLoading = useNoteDetailStore((s) => s.isLoading);

  useEffect(() => {
    if (selectedNoteId === null) {
      return;
    }
    const { note } = useNoteDetailStore.getState();
    if (note?.noteId === selectedNoteId) {
      return;
    }
    void useNoteDetailStore.getState().fetchNote(selectedNoteId);
  }, [selectedNoteId]);

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text dimColor>← ESC to go back</Text>
      {isLoading && note === null && <Text>Loading...</Text>}
      {note !== null && (
        <>
          <Text bold>{note.topic.label}</Text>
          {note.tags.length > 0 && (
            <Text dimColor>{note.tags.map((t) => t.label).join(" · ")}</Text>
          )}
          <Text wrap="wrap">{note.content}</Text>
        </>
      )}
    </Box>
  );
}
