import { Box, Text, useInput } from "ink";
import { NoteTabStrip } from "../components/NoteTabStrip.js";
import { useCardsStore } from "../store/cards.js";
import { useAppStore } from "../store/index.js";
import { useNotesStore } from "../store/notes.js";

export default function CardDetailScreen() {
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const selectedCardId = useAppStore((s) => s.selectedCardId);
  const closeCard = useAppStore((s) => s.closeCard);
  const cards = useCardsStore((s) => s.cards);
  const card = cards.find((c) => c.cardId === selectedCardId) ?? null;
  const cardCount = useNotesStore(
    (s) =>
      s.items.find((item) => item.noteId === selectedNoteId)?.cardCount ??
      cards.length,
  );

  useInput((_input, key) => {
    if (key.leftArrow) {
      closeCard();
    }
  });

  return (
    <Box flexDirection="column" flexGrow={1}>
      <NoteTabStrip activeTab="cards" cardCount={cardCount} />
      {card !== null && (
        <>
          <Text wrap="wrap">{card.front}</Text>
          <Text wrap="wrap">{card.back}</Text>
          <Text wrap="wrap">{card.anchorQuote}</Text>
        </>
      )}
    </Box>
  );
}
