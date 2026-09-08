import { Box, Text, useInput } from "ink";
import { useCardsStore } from "../store/cards.js";
import { useAppStore } from "../store/index.js";

export default function CardListScreen() {
  const selectedNoteId = useAppStore((s) => s.selectedNoteId);
  const cards = useCardsStore((s) => s.cards);
  const isLoading = useCardsStore((s) => s.isLoading);

  useInput(() => {
    return;
  });

  return (
    <Box key={selectedNoteId ?? "none"} flexDirection="column" flexGrow={1}>
      {isLoading && cards.length === 0 && <Text>Loading...</Text>}
      {cards.map((card) => (
        <Box key={card.cardId} flexDirection="column">
          <Text>{card.front}</Text>
          <Text dimColor>{card.back}</Text>
          <Text dimColor>{card.anchorQuote}</Text>
        </Box>
      ))}
    </Box>
  );
}
