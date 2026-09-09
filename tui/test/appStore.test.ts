import { beforeEach, describe, expect, it } from "vitest";
import type { AnchorLocation } from "../src/api/cards";
import { useAppStore } from "../src/store/index";

const NOTE_ID = "00000000-0000-4000-8000-000000000001";
const CARD_ID = "00000000-0000-4000-8000-000000000101";
const LOCATION: AnchorLocation = {
  blockIndex: 1,
  start: 4,
  end: 20,
  precision: "exact",
};

describe("useAppStore", () => {
  beforeEach(() => {
    useAppStore.setState({
      isNotesOverlayOpen: false,
      selectedIndex: 0,
      isDetailOpen: false,
      selectedNoteId: null,
      activeNoteTab: "note",
      selectedCardId: null,
      highlightedAnchor: null,
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

  it("jumps to a card's location in one write and drops the highlight on each leaving transition", () => {
    useAppStore.setState({
      isDetailOpen: true,
      selectedNoteId: NOTE_ID,
      activeNoteTab: "cards",
      selectedCardId: CARD_ID,
      highlightedAnchor: null,
    });

    useAppStore.getState().jumpToAnchor(CARD_ID, LOCATION);

    expect(useAppStore.getState()).toMatchObject({
      activeNoteTab: "note",
      selectedCardId: null,
      highlightedAnchor: { cardId: CARD_ID, location: LOCATION },
    });

    useAppStore.getState().setActiveNoteTab("cards");
    expect(useAppStore.getState().highlightedAnchor).toBeNull();

    useAppStore.setState({
      highlightedAnchor: { cardId: CARD_ID, location: LOCATION },
    });
    useAppStore.getState().openDetail(NOTE_ID);
    expect(useAppStore.getState().highlightedAnchor).toBeNull();

    useAppStore.setState({
      highlightedAnchor: { cardId: CARD_ID, location: LOCATION },
    });
    useAppStore.getState().closeDetail();
    expect(useAppStore.getState().highlightedAnchor).toBeNull();

    useAppStore.setState({
      isNotesOverlayOpen: true,
      highlightedAnchor: { cardId: CARD_ID, location: LOCATION },
    });
    useAppStore.getState().closeNotes();
    expect(useAppStore.getState().highlightedAnchor).toBeNull();
  });
});
