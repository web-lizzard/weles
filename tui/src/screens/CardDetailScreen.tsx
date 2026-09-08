import { Box, Text } from "ink";
import { useCardsStore } from "../store/cards.js";
import { useAppStore } from "../store/index.js";

export default function CardDetailScreen() {
  const selectedCardId = useAppStore((s) => s.selectedCardId);
  const cards = useCardsStore((s) => s.cards);
  const card = cards.find((c) => c.cardId === selectedCardId) ?? null;

  return (
    <Box flexDirection="column" flexGrow={1}>
      {card !== null && (
        <>
          <Text>{card.front}</Text>
          <Text wrap="wrap">{card.back}</Text>
          <Text wrap="wrap">{card.anchorQuote}</Text>
        </>
      )}
    </Box>
  );
}
