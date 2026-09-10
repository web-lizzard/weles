import { create } from "zustand";
import type { Grade } from "../api/sittings.js";

type SittingPhase =
  | "opening"
  | "nothing_due"
  | "presented"
  | "complete"
  | "error";

type LastAction =
  | { type: "open" }
  | { type: "reveal" }
  | { type: "grade"; grade: Grade };

type SittingState = {
  phase: SittingPhase;
  sittingId: string | null;
  cardId: string | null;
  front: string | null;
  back: string | null;
  isBackVisible: boolean;
  selectedGradeIndex: number;
  isSubmitting: boolean;
  error: { code: string; detail: string } | null;
  lastAction: LastAction | null;
};

type SittingActions = {
  open: () => Promise<void>;
  toggleBack: () => Promise<void>;
  moveSelection: (delta: 1 | -1) => void;
  submitGrade: (grade: Grade) => Promise<void>;
  retry: () => Promise<void>;
  reset: () => void;
};

const initialState: SittingState = {
  phase: "opening",
  sittingId: null,
  cardId: null,
  front: null,
  back: null,
  isBackVisible: false,
  selectedGradeIndex: 0,
  isSubmitting: false,
  error: null,
  lastAction: null,
};

export const useSittingStore = create<SittingState & SittingActions>(() => ({
  ...initialState,
  open: async () => {},
  toggleBack: async () => {},
  moveSelection: (_delta: 1 | -1) => {},
  submitGrade: async (_grade: Grade) => {},
  retry: async () => {},
  reset: () => {},
}));
