import { Box, useInput, useStdout } from "ink";
import { useDuePolling } from "./hooks/useDuePolling.js";
import CaptureScreen from "./screens/CaptureScreen.js";
import CardDetailScreen from "./screens/CardDetailScreen.js";
import CardListScreen from "./screens/CardListScreen.js";
import NoteDetailScreen from "./screens/NoteDetailScreen.js";
import NoteListOverlay from "./screens/NoteListOverlay.js";
import SittingOverlay from "./screens/SittingOverlay.js";
import { useAppStore } from "./store/index.js";

const DEFAULT_TERMINAL_ROWS = 24;
const DEFAULT_TERMINAL_COLUMNS = 80;
export const DUE_POLL_INTERVAL_MS = 15_000;

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
  const columns =
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS;

  useDuePolling(DUE_POLL_INTERVAL_MS);

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
      <Box position="relative" flexDirection="column" height={rows - 1}>
        <CaptureScreen />
        {isNotesOverlayOpen && (
          <Box
            position="absolute"
            top={0}
            left={0}
            width={columns}
            height={rows - 2}
            flexDirection="column"
            backgroundColor="black"
            padding={1}
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
          </Box>
        )}
        {isSittingOverlayOpen && (
          <Box
            position="absolute"
            top={0}
            left={0}
            width={columns}
            height={rows - 1}
            flexDirection="column"
            backgroundColor="black"
            padding={1}
          >
            <SittingOverlay />
          </Box>
        )}
      </Box>
    </Box>
  );
}
