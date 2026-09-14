import { Box, Text, useInput, useStdout } from "ink";
import { useState } from "react";
import wrapAnsi from "wrap-ansi";
import { NoteTabStrip } from "../components/NoteTabStrip.js";
import SourceViewport from "../components/SourceViewport.js";
import { panelBodyHeight } from "../lib/panelLayout.js";
import { useCardsStore } from "../store/cards.js";
import { useAppStore } from "../store/index.js";
import { useNotesStore } from "../store/notes.js";

const DEFAULT_TERMINAL_ROWS = 24;
const DEFAULT_TERMINAL_COLUMNS = 80;

export default function CardDetailScreen() {
  const { stdout } = useStdout();
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const selectedCardId = useAppStore((s) => s.selectedCardId);
  const closeCard = useAppStore((s) => s.closeCard);
  const jumpToAnchor = useAppStore((s) => s.jumpToAnchor);
  const cards = useCardsStore((s) => s.cards);
  const card = cards.find((c) => c.cardId === selectedCardId) ?? null;
  const cardCount = useNotesStore(
    (s) =>
      s.items.find((item) => item.noteId === selectedNoteId)?.cardCount ??
      cards.length,
  );
  const rows = stdout.rows > 0 ? stdout.rows : DEFAULT_TERMINAL_ROWS;
  const columns =
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS;
  const height = panelBodyHeight(rows, 0);
  const lines = card === null ? [] : buildCardLines(card, columns);

  const [offset, setOffset] = useState(0);

  useInput((_input, key) => {
    if (key.leftArrow) {
      closeCard();
      return;
    }
    if (key.return) {
      const selected = useCardsStore
        .getState()
        .cards.find(
          (item) => item.cardId === useAppStore.getState().selectedCardId,
        );
      if (selected !== undefined) {
        jumpToAnchor(selected.cardId, selected.anchorLocation);
      }
      return;
    }
    const maxOffset = Math.max(0, lines.length - 1);
    if (key.upArrow) {
      setOffset(Math.max(0, offset - 1));
      return;
    }
    if (key.downArrow) {
      setOffset(Math.min(maxOffset, offset + 1));
    }
  });

  return (
    <Box flexDirection="column" flexGrow={1}>
      <NoteTabStrip activeTab="cards" cardCount={cardCount} />
      {card !== null && (
        <SourceViewport lines={lines} offset={offset} height={height} />
      )}
      <Text dimColor>Enter jump to source · ← back</Text>
    </Box>
  );
}

function buildCardLines(
  card: { front: string; back: string; anchorQuote: string },
  columns: number,
): string[] {
  return [
    ...wrapAnsi(card.front, columns, { hard: true, trim: false }).split("\n"),
    ...wrapAnsi(card.back, columns, { hard: true, trim: false }).split("\n"),
    ...wrapAnsi(card.anchorQuote, columns, { hard: true, trim: false }).split(
      "\n",
    ),
  ];
}
