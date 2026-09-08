import { Box, Text, useInput } from "ink";
import { useEffect } from "react";
import { NoteTabStrip } from "../components/NoteTabStrip.js";
import { useAppStore } from "../store/index.js";
import { useNoteDetailStore } from "../store/noteDetail.js";
import { useNotesStore } from "../store/notes.js";

export default function NoteDetailScreen() {
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const setActiveNoteTab = useAppStore((s) => s.setActiveNoteTab);
  const note = useNoteDetailStore((s) => s.note);
  const isLoading = useNoteDetailStore((s) => s.isLoading);
  const cardCount = useNotesStore(
    (s) =>
      s.items.find((item) => item.noteId === selectedNoteId)?.cardCount ?? 0,
  );

  useEffect(() => {
    if (selectedNoteId !== null) {
      void useNoteDetailStore.getState().fetchNote(selectedNoteId);
    }
  }, [selectedNoteId]);

  useInput((_input, key) => {
    if (key.rightArrow && cardCount > 0) {
      setActiveNoteTab("cards");
    }
  });

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Text dimColor>← ESC to go back</Text>
      <NoteTabStrip activeTab="note" cardCount={cardCount} />
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
