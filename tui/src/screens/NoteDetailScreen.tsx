import { Chalk } from "chalk";
import { Box, Text, useInput, useStdout } from "ink";
import { useEffect, useState } from "react";
import type { AnchorLocation } from "../api/cards.js";
import type { NoteBlock } from "../api/notes.js";
import { NoteTabStrip } from "../components/NoteTabStrip.js";
import SourceViewport from "../components/SourceViewport.js";
import { renderMarkdownLines } from "../lib/markdown.js";
import { panelBodyHeight } from "../lib/panelLayout.js";
import { useAppStore } from "../store/index.js";
import { useNoteDetailStore } from "../store/noteDetail.js";
import { useNotesStore } from "../store/notes.js";

const DEFAULT_TERMINAL_ROWS = 24;
const DEFAULT_TERMINAL_COLUMNS = 80;
const INVERSE_ON = "[7m";
const INVERSE_OFF = "[27m";

const chalk = new Chalk();

export default function NoteDetailScreen() {
  const { stdout } = useStdout();
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const setActiveNoteTab = useAppStore((s) => s.setActiveNoteTab);
  const highlightedAnchor = useAppStore((s) => s.highlightedAnchor);
  const note = useNoteDetailStore((s) => s.note);
  const isLoading = useNoteDetailStore((s) => s.isLoading);
  const cardCount = useNotesStore(
    (s) =>
      s.items.find((item) => item.noteId === selectedNoteId)?.cardCount ?? 0,
  );
  const rows = stdout.rows > 0 ? stdout.rows : DEFAULT_TERMINAL_ROWS;
  const columns =
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS;
  const height = panelBodyHeight(rows, 0);

  const location = highlightedAnchor?.location ?? null;
  const { lines, anchorLineIndex } =
    note === null
      ? { lines: [], anchorLineIndex: null }
      : buildBodyLines(displayBlocks(note), location, columns);
  const initialOffset =
    anchorLineIndex === null
      ? 0
      : Math.min(anchorLineIndex, Math.max(0, lines.length - 1));

  const [offset, setOffset] = useState(initialOffset);
  const [syncKey, setSyncKey] = useState<string | null>(null);
  const nextSyncKey = `${selectedNoteId ?? ""}:${highlightedAnchor?.cardId ?? ""}:${location?.blockIndex ?? -1}:${location?.start ?? -1}`;
  if (nextSyncKey !== syncKey) {
    setSyncKey(nextSyncKey);
    if (offset !== initialOffset) {
      setOffset(initialOffset);
    }
  }
  const effectiveOffset = nextSyncKey !== syncKey ? initialOffset : offset;

  useEffect(() => {
    if (selectedNoteId !== null) {
      void useNoteDetailStore.getState().fetchNote(selectedNoteId);
    }
  }, [selectedNoteId]);

  useInput((_input, key) => {
    if (key.rightArrow && cardCount > 0) {
      setActiveNoteTab("cards");
      return;
    }
    const maxOffset = Math.max(0, lines.length - 1);
    if (key.upArrow) {
      setOffset(Math.max(0, effectiveOffset - 1));
      return;
    }
    if (key.downArrow) {
      setOffset(Math.min(maxOffset, effectiveOffset + 1));
      return;
    }
    if (key.pageUp) {
      setOffset(Math.max(0, effectiveOffset - height));
      return;
    }
    if (key.pageDown) {
      setOffset(Math.min(maxOffset, effectiveOffset + height));
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
            <SourceViewport
              lines={lines}
              offset={effectiveOffset}
              height={height}
            />
          </>
        )}
      </Box>
    </Box>
  );
}

function displayBlocks(note: {
  blocks: NoteBlock[];
  content: string;
}): NoteBlock[] {
  if (note.blocks.length > 0) {
    return note.blocks;
  }
  return [{ index: 0, text: note.content }];
}

function highlightBlockText(text: string, location: AnchorLocation): string {
  return (
    text.slice(0, location.start) +
    INVERSE_ON +
    text.slice(location.start, location.end) +
    INVERSE_OFF +
    text.slice(location.end)
  );
}

function buildBodyLines(
  blocks: NoteBlock[],
  location: AnchorLocation | null,
  columns: number,
): { lines: string[]; anchorLineIndex: number | null } {
  let anchorLineIndex: number | null = null;
  const lines: string[] = [];

  for (const block of blocks) {
    const isAnchored = location !== null && block.index === location.blockIndex;
    const text = isAnchored
      ? highlightBlockText(block.text, location)
      : block.text;
    if (isAnchored) {
      anchorLineIndex = lines.length;
    }
    lines.push(...renderMarkdownLines(text, columns, chalk));
  }

  return { lines, anchorLineIndex };
}
