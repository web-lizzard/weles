import { useEffect } from "react";
import { useNotesStore } from "../store/notes.js";

export function useNotesPolling(intervalMs: number): void {
  useEffect(() => {
    useNotesStore.getState().startPolling(intervalMs);
    return () => useNotesStore.getState().stopPolling();
  }, [intervalMs]);
}
