import { useInput } from "ink";
import CaptureScreen from "./screens/CaptureScreen.js";
import NoteListOverlay from "./screens/NoteListOverlay.js";
import { useAppStore } from "./store/index.js";

export default function App() {
  const isNotesOverlayOpen = useAppStore((state) => state.isNotesOverlayOpen);
  const closeNotes = useAppStore((state) => state.closeNotes);

  useInput((_input, key) => {
    if (key.escape && isNotesOverlayOpen) {
      closeNotes();
    }
  });

  return (
    <>
      <CaptureScreen />
      {isNotesOverlayOpen && <NoteListOverlay />}
    </>
  );
}
