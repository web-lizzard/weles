import { beforeEach, describe, expect, it } from "vitest";
import { useAppStore } from "../src/store/index";

describe("useAppStore", () => {
  beforeEach(() => {
    useAppStore.setState({
      isNotesOverlayOpen: false,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
    });
  });

  it("opens the detail view with the selected note id", () => {
    useAppStore.getState().openDetail("00000000-0000-4000-8000-000000000001");

    expect(useAppStore.getState().isDetailOpen).toBe(true);
    expect(useAppStore.getState().selectedNoteId).toBe(
      "00000000-0000-4000-8000-000000000001",
    );
  });

  it("clears detail state on closeDetail", () => {
    useAppStore.setState({
      isDetailOpen: true,
      selectedNoteId: "00000000-0000-4000-8000-000000000001",
    });

    useAppStore.getState().closeDetail();

    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useAppStore.getState().selectedNoteId).toBeNull();
  });

  it("resets overlay, selection, and detail state on closeNotes", () => {
    useAppStore.setState({
      isNotesOverlayOpen: true,
      selectedIndex: 3,
      isDetailOpen: true,
      selectedNoteId: "00000000-0000-4000-8000-000000000001",
    });

    useAppStore.getState().closeNotes();

    expect(useAppStore.getState().isNotesOverlayOpen).toBe(false);
    expect(useAppStore.getState().selectedIndex).toBe(0);
    expect(useAppStore.getState().isDetailOpen).toBe(false);
    expect(useAppStore.getState().selectedNoteId).toBeNull();
  });

  it("sets selectedIndex verbatim", () => {
    useAppStore.getState().setSelectedIndex(2);

    expect(useAppStore.getState().selectedIndex).toBe(2);
  });
});
