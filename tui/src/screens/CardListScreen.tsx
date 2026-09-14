import { Box, Text, useInput, useStdout } from "ink";
import { useEffect, useState } from "react";
import type { Card } from "../api/cards.js";
import { NoteTabStrip } from "../components/NoteTabStrip.js";
import { listWindow, panelBodyHeight } from "../lib/panelLayout.js";
import { useCardsStore } from "../store/cards.js";
import { useAppStore } from "../store/index.js";
import { useNotesStore } from "../store/notes.js";

const BACK_PREVIEW_LENGTH = 80;
const DEFAULT_TERMINAL_ROWS = 24;
const ROWS_PER_CARD = 4; // front + preview + anchor + gap

export default function CardListScreen() {
  const { stdout } = useStdout();
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const setActiveNoteTab = useAppStore((s) => s.setActiveNoteTab);
  const openCard = useAppStore((s) => s.openCard);
  const cards = useCardsStore((s) => s.cards);
  const isLoading = useCardsStore((s) => s.isLoading);
  const cardCount = useNotesStore(
    (s) =>
      s.items.find((item) => item.noteId === selectedNoteId)?.cardCount ??
      cards.length,
  );
  const [selectedIndex, setSelectedIndex] = useState(0);
  const maxIndex = Math.max(0, cards.length - 1);
  const effectiveIndex = Math.min(selectedIndex, maxIndex);

  const rows = stdout.rows > 0 ? stdout.rows : DEFAULT_TERMINAL_ROWS;
  const windowSize = Math.max(
    1,
    Math.floor(panelBodyHeight(rows, 0) / ROWS_PER_CARD),
  );
  const { start: windowStart, size: effectiveWindowSize } = listWindow(
    effectiveIndex,
    cards.length,
    windowSize,
  );
  const visibleCards = cards.slice(
    windowStart,
    windowStart + effectiveWindowSize,
  );

  useEffect(() => {
    if (selectedNoteId === null) {
      return;
    }
    void useCardsStore.getState().fetchCards(selectedNoteId);
  }, [selectedNoteId]);

  useInput((input, key) => {
    if (key.leftArrow) {
      setActiveNoteTab("note");
      return;
    }

    if (input === "r") {
      void useCardsStore.getState().refresh();
      return;
    }

    if (cards.length === 0) {
      return;
    }

    if (key.upArrow) {
      setSelectedIndex(clamp(effectiveIndex - 1, 0, maxIndex));
      return;
    }

    if (key.downArrow) {
      setSelectedIndex(clamp(effectiveIndex + 1, 0, maxIndex));
      return;
    }

    if (key.pageUp) {
      setSelectedIndex(clamp(effectiveIndex - windowSize, 0, maxIndex));
      return;
    }

    if (key.pageDown) {
      setSelectedIndex(clamp(effectiveIndex + windowSize, 0, maxIndex));
      return;
    }

    if (key.return) {
      openCard(cards[effectiveIndex].cardId);
    }
  });

  return (
    <Box key={selectedNoteId ?? "none"} flexDirection="column" flexGrow={1}>
      <NoteTabStrip activeTab="cards" cardCount={cardCount} />
      {isLoading && cards.length === 0 && <Text>Loading...</Text>}
      {cards.length === 0 && <Text>No cards for this note</Text>}
      <Box flexDirection="column" flexGrow={1}>
        {visibleCards.map((card, index) => (
          <CardRow
            key={card.cardId}
            card={card}
            isSelected={windowStart + index === effectiveIndex}
          />
        ))}
      </Box>
    </Box>
  );
}

function CardRow({ card, isSelected }: { card: Card; isSelected: boolean }) {
  const color = isSelected ? "blue" : undefined;
  const preview =
    card.back.length > BACK_PREVIEW_LENGTH
      ? `${card.back.slice(0, BACK_PREVIEW_LENGTH)}…`
      : card.back;

  return (
    <Box flexDirection="column">
      <Text color={color}>{card.front}</Text>
      <Text dimColor={color === undefined} color={color}>
        {preview}
      </Text>
      <Text dimColor={color === undefined} color={color}>
        {card.anchorQuote}
      </Text>
    </Box>
  );
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
