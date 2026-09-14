import { Chalk } from "chalk";
import { Box, Text, useInput, useStdout } from "ink";
import TextInput from "ink-text-input";
import type { ReactNode } from "react";
import { useEffect, useLayoutEffect, useState } from "react";
import ActivityIndicator from "../components/ActivityIndicator.js";
import ConversationHistory from "../components/ConversationHistory.js";
import DraftRegion from "../components/DraftRegion.js";
import InputFrame from "../components/InputFrame.js";
import StatusLine from "../components/StatusLine.js";
import { clampDraftOffset, layoutCapture } from "../lib/captureLayout.js";
import { renderConversationLines } from "../lib/conversationLines.js";
import { renderDraftLines } from "../lib/draftLines.js";
import { PANEL_CHROME_ROWS, panelBodyHeight } from "../lib/panelLayout.js";
import { CLEAR_SCREEN_AND_SCROLLBACK } from "../lib/terminal.js";
import { useChatStore } from "../store/chat.js";
import { useAppStore } from "../store/index.js";

const DEFAULT_TERMINAL_ROWS = 24;
const DEFAULT_TERMINAL_COLUMNS = 80;
const APPROVE_COMMAND = "/approve";
const NOTES_COMMAND = "/notes";
const REMEMBER_COMMAND = "/remember";
const FRAME_ROWS = 3;
const STATUS_LINE_ROWS = 1;
// Blank row that keeps the conversation from butting against the input area.
const INPUT_GAP_ROWS = 1;
// One row of text plus marginY={1} above and below.
const MARGINED_ROWS_OVERHEAD = 2;
const TOPIC_HEADING_ROWS = 1 + MARGINED_ROWS_OVERHEAD;
// The rule under the draft, plus the more-above/more-below markers when the
// draft overflows its window.
const DRAFT_RULE_ROWS = 1;
const DRAFT_MARKER_ROWS = 2;
const COVERAGE_BANNER_TEXT =
  "✓ This topic seems well covered — keep going, or wrap up when you're ready.";

const chalk = new Chalk();

type CaptureScreenProps = {
  panel?: ReactNode | null;
};

export default function CaptureScreen({
  panel = null,
}: CaptureScreenProps = {}) {
  const { stdout, write } = useStdout();
  const initSession = useChatStore((state) => state.initSession);
  const sendUserMessage = useChatStore((state) => state.sendUserMessage);
  const approveDraft = useChatStore((state) => state.approveDraft);
  const transcript = useChatStore((state) => state.transcript);
  const currentReply = useChatStore((state) => state.currentReply);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const topic = useChatStore((state) => state.topic);
  const turnStartedAt = useChatStore((state) => state.turnStartedAt);
  const coverageConfidence = useChatStore((state) => state.coverageConfidence);
  const streamError = useChatStore((state) => state.streamError);
  const draft = useChatStore((state) => state.draft);
  const approvalReceipt = useChatStore((state) => state.approvalReceipt);
  const historyEpoch = useChatStore((state) => state.historyEpoch);
  const isNotesOverlayOpen = useAppStore((state) => state.isNotesOverlayOpen);
  const isSittingOverlayOpen = useAppStore(
    (state) => state.isSittingOverlayOpen,
  );

  const [inputValue, setInputValue] = useState("");
  const [committedLineCount, setCommittedLineCount] = useState(0);
  const [draftOffset, setDraftOffset] = useState(0);
  const [draftIdentity, setDraftIdentity] = useState<string | null>(
    draft?.topic ?? null,
  );

  const rows = stdout.rows > 0 ? stdout.rows : DEFAULT_TERMINAL_ROWS;
  const columns =
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS;

  const hasStreamError = streamError !== null;
  const hasCoverageBanner =
    coverageConfidence !== null && coverageConfidence >= 1;
  const showBrand = historyEpoch === 0;
  const showReceipt = approvalReceipt;

  const { lines, stableLineCount } = renderConversationLines({
    showBrand,
    showReceipt,
    transcript,
    currentReply,
    columns,
    chalk,
  });

  const draftLines =
    draft !== null ? renderDraftLines(draft, columns, chalk) : null;

  const bannerRows = hasCoverageBanner
    ? wrappedRowCount(COVERAGE_BANNER_TEXT, columns) + MARGINED_ROWS_OVERHEAD
    : 0;
  const errorRows = hasStreamError
    ? wrappedRowCount(streamError.detail, columns) + MARGINED_ROWS_OVERHEAD
    : 0;
  const topicRows = topic !== null ? TOPIC_HEADING_ROWS : 0;
  const draftChromeRows =
    draftLines === null
      ? 0
      : DRAFT_RULE_ROWS +
        (draftLines.length > Math.floor((rows - 1) / 2)
          ? DRAFT_MARKER_ROWS
          : 0);
  const indicatorRows = panel === null && turnStartedAt !== null ? 1 : 0;
  const chromeRows =
    topicRows +
    draftChromeRows +
    bannerRows +
    errorRows +
    (panel !== null
      ? PANEL_CHROME_ROWS + panelBodyHeight(rows, 0)
      : INPUT_GAP_ROWS + indicatorRows + FRAME_ROWS + STATUS_LINE_ROWS);

  const nextDraftIdentity = draft?.topic ?? null;
  if (nextDraftIdentity !== draftIdentity) {
    setDraftIdentity(nextDraftIdentity);
    setDraftOffset(0);
  }
  const effectiveDraftOffset =
    nextDraftIdentity !== draftIdentity ? 0 : draftOffset;

  const layout = layoutCapture({
    rows,
    chromeRows,
    draftLines,
    draftOffset: effectiveDraftOffset,
    conversationLines: lines,
    stableLineCount,
    committedLineCount,
  });

  const canScrollDraft =
    draft !== null && !isNotesOverlayOpen && !isSittingOverlayOpen;

  useInput(
    (_input, key) => {
      if (!canScrollDraft || layout.draftWindow === null) {
        return;
      }
      if (key.upArrow) {
        setDraftOffset(
          clampDraftOffset(
            effectiveDraftOffset - 1,
            draftLines?.length ?? 0,
            layout.draftWindow.height,
          ),
        );
      } else if (key.downArrow) {
        setDraftOffset(
          clampDraftOffset(
            effectiveDraftOffset + 1,
            draftLines?.length ?? 0,
            layout.draftWindow.height,
          ),
        );
      }
    },
    { isActive: canScrollDraft },
  );

  // biome-ignore lint/correctness/useExhaustiveDependencies: reset the commit cursor whenever a new epoch starts
  useEffect(() => {
    setCommittedLineCount(0);
  }, [historyEpoch]);

  useEffect(() => {
    if (layout.committedLineCount !== committedLineCount) {
      setCommittedLineCount(layout.committedLineCount);
    }
  });

  useLayoutEffect(() => {
    if (historyEpoch > 0) {
      write(CLEAR_SCREEN_AND_SCROLLBACK);
    }
  }, [historyEpoch, write]);

  useEffect(() => {
    void initSession();
  }, [initSession]);

  const handleSubmit = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) {
      return;
    }
    setInputValue("");
    if (trimmed === NOTES_COMMAND) {
      useAppStore.getState().openNotes();
      return;
    }
    if (trimmed === REMEMBER_COMMAND) {
      useAppStore.getState().openSittingOverlay();
      return;
    }
    if (trimmed === APPROVE_COMMAND) {
      void approveDraft();
      return;
    }
    void sendUserMessage(trimmed);
  };
  const isApproveCommand = inputValue.trim() === APPROVE_COMMAND;
  const isNotesCommand = inputValue.trim() === NOTES_COMMAND;
  const isRememberCommand = inputValue.trim() === REMEMBER_COMMAND;

  return (
    <Box flexDirection="column" flexGrow={1}>
      <ConversationHistory
        epoch={historyEpoch}
        lines={lines.slice(0, committedLineCount)}
      />
      {topic !== null && <TopicHeading topic={topic} />}
      {layout.draftWindow !== null && (
        <DraftRegion window={layout.draftWindow} />
      )}
      <Box
        flexDirection="column"
        flexGrow={panel === null ? 1 : 0}
        flexShrink={1}
        overflow="hidden"
      >
        {Array.from({ length: Math.max(0, layout.fillerRows) }).map(
          (_, index) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: filler rows have no stable id
            <Text key={index}> </Text>
          ),
        )}
        {layout.conversationTail.map((line, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: the tail window has no stable id
          <Text key={index}>{line}</Text>
        ))}
      </Box>
      <CoverageBanner coverageConfidence={coverageConfidence} />
      {streamError !== null && <StatusBar error={streamError} />}
      {panel === null && <Box height={INPUT_GAP_ROWS} flexShrink={0} />}
      {panel === null && turnStartedAt !== null && (
        <ActivityIndicator startedAt={turnStartedAt} />
      )}
      {panel !== null ? (
        panel
      ) : (
        <>
          <InputFrame columns={columns}>
            <UserLabel />
            <Text
              color={
                isApproveCommand || isNotesCommand || isRememberCommand
                  ? "green"
                  : undefined
              }
            >
              <TextInput
                value={inputValue}
                onChange={setInputValue}
                onSubmit={handleSubmit}
                focus={
                  !isStreaming && !isNotesOverlayOpen && !isSittingOverlayOpen
                }
              />
            </Text>
          </InputFrame>
          <StatusLine columns={columns} showApproveHint={draft !== null} />
        </>
      )}
    </Box>
  );
}

function UserLabel() {
  return <Text>🧑 You: </Text>;
}

function TopicHeading({ topic }: { topic: string }) {
  return (
    <Box marginY={1} flexShrink={0}>
      <Text bold>Topic: {topic}</Text>
    </Box>
  );
}

function CoverageBanner({
  coverageConfidence,
}: {
  coverageConfidence: number | null;
}) {
  if (coverageConfidence === null || coverageConfidence < 1) {
    return null;
  }

  return (
    <Box marginY={1}>
      <Text color="green">{COVERAGE_BANNER_TEXT}</Text>
    </Box>
  );
}

function StatusBar({ error }: { error: { code: string; detail: string } }) {
  return (
    <Box marginY={1}>
      <Text color="red">{error.detail}</Text>
    </Box>
  );
}

function wrappedRowCount(text: string, columns: number): number {
  const width = columns > 0 ? columns : 1;
  return Math.max(1, Math.ceil(text.length / width));
}
