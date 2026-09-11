import { create } from "zustand";
import {
  currentCard,
  type Grade,
  gradeCard,
  openSitting,
  rejectCard,
  revealBack,
  SITTING_EXPIRED,
  SittingHttpError,
} from "../api/sittings.js";
import { useDueStore } from "./due.js";

type SittingPhase =
  | "opening"
  | "nothing_due"
  | "presented"
  | "complete"
  | "error";

type LastAction =
  | { type: "open" }
  | { type: "reveal" }
  | { type: "grade"; grade: Grade }
  | { type: "reject" }
  | { type: "reject_reread" };

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
  isResumed: boolean;
  outstandingCount: number;
  notice: string | null;
};

type SittingActions = {
  open: () => Promise<void>;
  toggleBack: () => Promise<void>;
  moveSelection: (delta: 1 | -1) => void;
  submitGrade: (grade: Grade) => Promise<void>;
  rejectCurrentCard: () => Promise<void>;
  retry: () => Promise<void>;
  reset: () => void;
};

const GRADE_COUNT = 4;

const SITTING_EXPIRED_NOTICE =
  "Your previous review session expired; that grade was not recorded.";

let revealBackInFlight = false;

type SittingStoreSet = (
  partial:
    | Partial<SittingState>
    | ((state: SittingState) => Partial<SittingState>),
) => void;

type SittingStoreGet = () => SittingState & SittingActions;

async function recoverFromSittingExpired(
  set: SittingStoreSet,
  get: SittingStoreGet,
): Promise<void> {
  set({
    sittingId: null,
    cardId: null,
    front: null,
    back: null,
    isBackVisible: false,
    isSubmitting: false,
    error: null,
    notice: SITTING_EXPIRED_NOTICE,
    phase: "opening",
  });
  await get().open();
}

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
  isResumed: false,
  outstandingCount: 0,
  notice: null,
};

function sittingHttpErrorState(error: SittingHttpError): Partial<SittingState> {
  return {
    phase: "error",
    error: { code: error.code, detail: error.detail },
    isSubmitting: false,
  };
}

async function applyCurrentCardAfterReject(
  set: SittingStoreSet,
  get: SittingStoreGet,
  sittingId: string,
): Promise<void> {
  try {
    const result = await currentCard(sittingId);
    if (result.due != null) {
      useDueStore.getState().applyPartition(result.due);
    }
    if (result.sittingComplete || result.cardId === null) {
      set({
        phase: "complete",
        sittingId: result.sittingId,
        cardId: null,
        front: null,
        back: null,
        isBackVisible: false,
        selectedGradeIndex: 0,
        error: null,
        isSubmitting: false,
        isResumed: false,
        outstandingCount: result.outstandingCount,
        notice: null,
        lastAction: null,
      });
      return;
    }
    set({
      phase: "presented",
      sittingId: result.sittingId,
      cardId: result.cardId,
      front: result.front,
      back: null,
      isBackVisible: false,
      selectedGradeIndex: 0,
      error: null,
      isSubmitting: false,
      isResumed: false,
      outstandingCount: result.outstandingCount,
      notice: null,
      lastAction: null,
    });
  } catch (error) {
    if (error instanceof SittingHttpError) {
      if (error.code === SITTING_EXPIRED) {
        await recoverFromSittingExpired(set, get);
      } else {
        set(sittingHttpErrorState(error));
      }
    } else {
      throw error;
    }
  }
}

export const useSittingStore = create<SittingState & SittingActions>(
  (set, get) => ({
    ...initialState,
    open: async () => {
      const state = get();
      if (
        state.phase === "presented" ||
        state.phase === "nothing_due" ||
        state.phase === "complete"
      ) {
        return;
      }
      if (state.phase === "opening" && state.lastAction?.type === "open") {
        return;
      }
      set({ lastAction: { type: "open" }, error: null });
      try {
        const result = await openSitting();
        if (result.kind === "nothing_due") {
          set({
            phase: "nothing_due",
            sittingId: null,
            cardId: null,
            front: null,
            back: null,
            isBackVisible: false,
            selectedGradeIndex: 0,
            error: null,
            isResumed: false,
            outstandingCount: 0,
          });
          return;
        }
        if (result.due != null) {
          useDueStore.getState().applyPartition(result.due);
        }
        set({
          phase: "presented",
          sittingId: result.sittingId,
          cardId: result.cardId,
          front: result.front,
          back: null,
          isBackVisible: false,
          selectedGradeIndex: 0,
          error: null,
          isResumed: result.kind === "resumed",
          outstandingCount: result.outstandingCount,
        });
      } catch (error) {
        if (error instanceof SittingHttpError) {
          set(sittingHttpErrorState(error));
        } else {
          throw error;
        }
      }
    },
    toggleBack: async () => {
      const state = get();
      if (
        state.phase !== "presented" ||
        state.sittingId === null ||
        state.cardId === null
      ) {
        return;
      }

      if (state.isBackVisible) {
        set({ isBackVisible: false });
        return;
      }

      if (state.back !== null) {
        set({ isBackVisible: true });
        return;
      }

      if (revealBackInFlight) {
        return;
      }

      revealBackInFlight = true;
      set({ lastAction: { type: "reveal" }, error: null });
      try {
        const revealed = await revealBack(state.sittingId, state.cardId);
        set({ isBackVisible: true, back: revealed.back });
      } catch (error) {
        if (error instanceof SittingHttpError) {
          if (error.code === SITTING_EXPIRED) {
            await recoverFromSittingExpired(set, get);
          } else {
            set(sittingHttpErrorState(error));
          }
        } else {
          throw error;
        }
      } finally {
        revealBackInFlight = false;
      }
    },
    moveSelection: (delta: 1 | -1) => {
      set((state) => ({
        selectedGradeIndex:
          (state.selectedGradeIndex + delta + GRADE_COUNT) % GRADE_COUNT,
      }));
    },
    submitGrade: async (grade: Grade) => {
      const state = get();
      if (state.sittingId === null || state.cardId === null) {
        return;
      }
      if (state.isSubmitting) {
        return;
      }

      const { sittingId, cardId } = state;
      set({
        lastAction: { type: "grade", grade },
        error: null,
        isSubmitting: true,
      });
      try {
        const result = await gradeCard(sittingId, cardId, grade);
        if (result.due != null) {
          useDueStore.getState().applyPartition(result.due);
        }
        if (result.sittingComplete || result.nextCardId === null) {
          set({
            phase: "complete",
            sittingId: result.sittingId,
            cardId: null,
            front: null,
            back: null,
            isBackVisible: false,
            selectedGradeIndex: 0,
            error: null,
            isSubmitting: false,
            isResumed: false,
            outstandingCount: result.outstandingCount,
            notice: null,
          });
          return;
        }
        set({
          phase: "presented",
          sittingId: result.sittingId,
          cardId: result.nextCardId,
          front: result.nextFront,
          back: null,
          isBackVisible: false,
          selectedGradeIndex: 0,
          error: null,
          isSubmitting: false,
          isResumed: false,
          outstandingCount: result.outstandingCount,
          notice: null,
        });
      } catch (error) {
        if (error instanceof SittingHttpError) {
          if (error.code === SITTING_EXPIRED) {
            await recoverFromSittingExpired(set, get);
          } else {
            set(sittingHttpErrorState(error));
          }
        } else {
          throw error;
        }
      }
    },
    rejectCurrentCard: async () => {
      const state = get();
      if (state.sittingId === null || state.cardId === null) {
        return;
      }
      if (state.isSubmitting) {
        return;
      }

      const { sittingId, cardId } = state;
      set({
        lastAction: { type: "reject" },
        error: null,
        isSubmitting: true,
      });
      try {
        await rejectCard(sittingId, cardId);
        set({ lastAction: { type: "reject_reread" } });
        await applyCurrentCardAfterReject(set, get, sittingId);
      } catch (error) {
        if (error instanceof SittingHttpError) {
          if (error.code === SITTING_EXPIRED) {
            await recoverFromSittingExpired(set, get);
          } else {
            set(sittingHttpErrorState(error));
          }
        } else {
          throw error;
        }
      }
    },
    retry: async () => {
      const state = get();
      const { lastAction } = state;
      if (lastAction === null) {
        return;
      }
      if (lastAction.type === "open") {
        await get().open();
      } else if (lastAction.type === "reveal") {
        await get().toggleBack();
      } else if (lastAction.type === "reject_reread") {
        if (state.sittingId === null) {
          return;
        }
        set({ error: null, isSubmitting: true });
        await applyCurrentCardAfterReject(set, get, state.sittingId);
      } else if (lastAction.type === "reject") {
        await get().rejectCurrentCard();
      } else {
        await get().submitGrade(lastAction.grade);
      }
    },
    reset: () => {
      revealBackInFlight = false;
      set({ ...initialState });
    },
  }),
);
