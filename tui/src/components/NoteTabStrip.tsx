import { Box, Text } from "ink";
import type { NoteTab } from "../store/index.js";

export function NoteTabStrip({
  activeTab,
  cardCount,
}: {
  activeTab: NoteTab;
  cardCount: number;
}) {
  return (
    <Box flexDirection="row" gap={1}>
      <TabLabel label="Note" isActive={activeTab === "note"} />
      <TabLabel label="Cards" isActive={activeTab === "cards"} />
      <Text dimColor>
        {cardCount} {cardCount === 1 ? "card" : "cards"}
      </Text>
    </Box>
  );
}

function TabLabel({ label, isActive }: { label: string; isActive: boolean }) {
  if (isActive) {
    return (
      <Text backgroundColor="blue" color="black">
        {"\x1B[44m"}
        {label}
      </Text>
    );
  }

  return <Text dimColor>{label}</Text>;
}
