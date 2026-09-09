import { Box, Text, useInput } from "ink";
import { useEffect } from "react";
import type { AnchorLocation } from "../api/cards.js";
import type { NoteBlock } from "../api/notes.js";
import { NoteTabStrip } from "../components/NoteTabStrip.js";
import { useAppStore } from "../store/index.js";
import { useNoteDetailStore } from "../store/noteDetail.js";
import { useNotesStore } from "../store/notes.js";

const INVERSE_ON = "\u001b[7m";
const INVERSE_OFF = "\u001b[27m";

function displayBlocks(note: {
  blocks: NoteBlock[];
  content: string;
}): NoteBlock[] {
  if (note.blocks.length > 0) {
    return note.blocks;
  }
  return [{ index: 0, text: note.content }];
}

function NoteBlockText({
  block,
  location,
}: {
  block: NoteBlock;
  location: AnchorLocation | null;
}) {
  if (location === null || block.index !== location.blockIndex) {
    return <Text wrap="wrap">{block.text}</Text>;
  }
  return (
    <Text wrap="wrap">
      {block.text.slice(0, location.start)}
      {INVERSE_ON}
      {block.text.slice(location.start, location.end)}
      {INVERSE_OFF}
      {block.text.slice(location.end)}
    </Text>
  );
}

export default function NoteDetailScreen() {
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const setActiveNoteTab = useAppStore((s) => s.setActiveNoteTab);
  const highlightedAnchor = useAppStore((s) => s.highlightedAnchor);
  const note = useNoteDetailStore((s) => s.note);
  const isLoading = useNoteDetailStore((s) => s.isLoading);
  const cardCount = useNotesStore(
    (s) =>
      s.items.find((item) => item.noteId === selectedNoteId)?.cardCount ?? 0,
  );
  const location = highlightedAnchor?.location ?? null;
  const visibleBlocks =
    note === null
      ? []
      : location === null
        ? displayBlocks(note)
        : displayBlocks(note).filter(
            (block) => block.index >= location.blockIndex,
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
            {highlightedAnchor !== null && location === null && (
              <Text>Source fragment was not found in this note.</Text>
            )}
            {visibleBlocks.map((block) => (
              <NoteBlockText
                key={block.index}
                block={block}
                location={location}
              />
            ))}
          </>
        )}
      </Box>
    </Box>
  );
}
