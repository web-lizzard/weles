import { Box, Text } from "ink";
import { useEffect } from "react";
import { useAppStore } from "../store/index.js";
import { useNoteDetailStore } from "../store/noteDetail.js";

export default function NoteDetailScreen() {
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const note = useNoteDetailStore((s) => s.note);
  const isLoading = useNoteDetailStore((s) => s.isLoading);

  useEffect(() => {
    if (selectedNoteId !== null) {
      void useNoteDetailStore.getState().fetchNote(selectedNoteId);
    }
  }, [selectedNoteId]);

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text dimColor>← ESC to go back</Text>
      <Box marginTop={1} flexDirection="column" gap={1} flexGrow={1}>
        {isLoading && note === null && <Text>Loading...</Text>}
        {note !== null && (
          <>
            <Text bold>{note.topic.label}</Text>
            {note.tags.length > 0 && (
              <Text>
                <Text dimColor>Tags: </Text>
                <Text dimColor>
                  {note.tags.map((t) => t.label).join(" · ")}
                </Text>
              </Text>
            )}
            <Text wrap="wrap">{note.content}</Text>
          </>
        )}
      </Box>
    </Box>
  );
}
