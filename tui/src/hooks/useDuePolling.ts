import { useEffect } from "react";
import { useDueStore } from "../store/due.js";

export function useDuePolling(intervalMs: number): void {
  useEffect(() => {
    useDueStore.getState().startPolling(intervalMs);
    return () => useDueStore.getState().stopPolling();
  }, [intervalMs]);
}
