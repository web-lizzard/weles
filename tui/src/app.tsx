import { useInput } from "ink";
import CaptureScreen from "./screens/CaptureScreen.js";
import { useAppStore } from "./store/index.js";

export default function App() {
  const isNotesOverlayOpen = useAppStore((state) => state.isNotesOverlayOpen);
  const closeNotes = useAppStore((state) => state.closeNotes);

  useInput(() => {});

  return <CaptureScreen />;
}
