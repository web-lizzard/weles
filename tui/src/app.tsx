import { Box, useInput, useStdout } from "ink";
import type { ReactNode } from "react";
import BottomPanel from "./components/BottomPanel.js";
import { useDuePolling } from "./hooks/useDuePolling.js";
import CaptureScreen from "./screens/CaptureScreen.js";
import CardDetailScreen from "./screens/CardDetailScreen.js";
import CardListScreen from "./screens/CardListScreen.js";
import NoteDetailScreen from "./screens/NoteDetailScreen.js";
import NoteListOverlay from "./screens/NoteListOverlay.js";
import SittingOverlay from "./screens/SittingOverlay.js";
import { useAppStore } from "./store/index.js";

const DEFAULT_TERMINAL_ROWS = 24;
export const DUE_POLL_INTERVAL_MS = 15_000;

const LIST_HINTS = "↑↓ select · Enter open · ← ESC to go back";
const CARD_DETAIL_HINTS = "Enter jump to source · ← back";
const SITTING_HINTS = "← ESC to go back";

export default function App() {
  const { stdout } = useStdout();
  const isNotesOverlayOpen = useAppStore((state) => state.isNotesOverlayOpen);
  const isSittingOverlayOpen = useAppStore(
    (state) => state.isSittingOverlayOpen,
  );
  const isDetailOpen = useAppStore((state) => state.isDetailOpen);
  const activeNoteTab = useAppStore((state) => state.activeNoteTab);
  const selectedCardId = useAppStore((state) => state.selectedCardId);
  const closeNotes = useAppStore((state) => state.closeNotes);
  const closeDetail = useAppStore((state) => state.closeDetail);
  const rows = stdout.rows > 0 ? stdout.rows : DEFAULT_TERMINAL_ROWS;

  useDuePolling(DUE_POLL_INTERVAL_MS);

  const panel: ReactNode | null = isSittingOverlayOpen ? (
    <BottomPanel hints={SITTING_HINTS}>
      <SittingOverlay />
    </BottomPanel>
  ) : isNotesOverlayOpen ? (
    <BottomPanel
      hints={notesPanelHints(isDetailOpen, activeNoteTab, selectedCardId)}
    >
      {isDetailOpen ? (
        selectedCardId !== null ? (
          <CardDetailScreen />
        ) : activeNoteTab === "cards" ? (
          <CardListScreen />
        ) : (
          <NoteDetailScreen />
        )
      ) : (
        <NoteListOverlay />
      )}
    </BottomPanel>
  ) : null;

  useInput((_input, key) => {
    if (!key.escape) {
      return;
    }

    if (isDetailOpen) {
      closeDetail();
      return;
    }

    if (isNotesOverlayOpen) {
      closeNotes();
      return;
    }

    // Sitting Esc ladder (source view → reject confirm → leave sitting) lives in
    // SittingOverlay only; handling it here would close the overlay on the first
    // Esc while the source view is open.
  });

  return (
    <Box flexDirection="column" height={rows}>
      <CaptureScreen panel={panel} />
    </Box>
  );
}

function notesPanelHints(
  isDetailOpen: boolean,
  activeNoteTab: "note" | "cards",
  selectedCardId: string | null,
): string {
  if (!isDetailOpen) {
    return LIST_HINTS;
  }
  if (selectedCardId !== null) {
    return CARD_DETAIL_HINTS;
  }
  if (activeNoteTab === "cards") {
    return LIST_HINTS;
  }
  return "→ cards · ← ESC to go back";
}
