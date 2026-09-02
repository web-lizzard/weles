import { Box, Text, useStdout } from "ink";
import TextInput from "ink-text-input";
import { useEffect, useState } from "react";
import {
  type Draft,
  type TranscriptEntry,
  useChatStore,
} from "../store/chat.js";

const WELES_TAGLINE = "wisdom through questions";
const DEFAULT_TERMINAL_ROWS = 24;
const DEFAULT_TERMINAL_COLUMNS = 80;
const APPROVE_COMMAND = "/approve";

export default function CaptureScreen() {
  const { stdout } = useStdout();
  const initSession = useChatStore((state) => state.initSession);
  const sendUserMessage = useChatStore((state) => state.sendUserMessage);
  const approveDraft = useChatStore((state) => state.approveDraft);
  const transcript = useChatStore((state) => state.transcript);
  const currentReply = useChatStore((state) => state.currentReply);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const topic = useChatStore((state) => state.topic);
  const coverageConfidence = useChatStore((state) => state.coverageConfidence);
  const streamError = useChatStore((state) => state.streamError);
  const draft = useChatStore((state) => state.draft);
  const approved = useChatStore((state) => state.approved);

  const [inputValue, setInputValue] = useState("");
  const hasTopic = topic !== null;
  const hasStreamError = streamError !== null;
  const hasCoverageBanner =
    coverageConfidence !== null && coverageConfidence >= 1;
  const hasDraft = draft !== null || approved;
  const showBrand = shouldShowWelesBrand(
    stdout.rows,
    transcript,
    hasTopic,
    isStreaming,
    hasStreamError,
    hasCoverageBanner,
    hasDraft,
  );
  const separator = "─".repeat(
    stdout.columns > 0 ? stdout.columns : DEFAULT_TERMINAL_COLUMNS,
  );

  useEffect(() => {
    void initSession();
  }, [initSession]);

  const handleSubmit = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) {
      return;
    }
    setInputValue("");
    if (trimmed === APPROVE_COMMAND) {
      void approveDraft();
      return;
    }
    void sendUserMessage(trimmed);
  };
  const isApproveCommand = inputValue.trim() === APPROVE_COMMAND;

  return (
    <Box flexDirection="column">
      {showBrand && <WelesBrand separator={separator} />}
      {hasTopic && <TopicHeading topic={topic} />}
      <Box flexDirection="column" flexGrow={1}>
        {transcript.map((entry, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: append-only transcript entries have no stable id
          <TranscriptLine key={index} entry={entry} />
        ))}
        {currentReply.length > 0 && (
          <Text>
            <WelesAgentLabel />
            {currentReply}
          </Text>
        )}
      </Box>
      {approved ? (
        <ApprovedPanel />
      ) : (
        <DraftNotePanel draft={draft} separator={separator} />
      )}
      <CoverageBanner coverageConfidence={coverageConfidence} />
      {streamError !== null && <StatusBar error={streamError} />}
      <Box>
        <UserLabel />
        <Text color={isApproveCommand ? "green" : undefined}>
          <TextInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSubmit}
            focus={!isStreaming && !approved}
          />
        </Text>
      </Box>
    </Box>
  );
}

function UserLabel() {
  return <Text>🧑 You: </Text>;
}

function WelesAgentLabel() {
  return <Text color="yellow">🦉 Weles: </Text>;
}

function WelesBrand({ separator }: { separator: string }) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text>
        <Text color="yellow">Weles:</Text>
        <Text> {WELES_TAGLINE}</Text>
      </Text>
      <Text dimColor>{separator}</Text>
    </Box>
  );
}

function TopicHeading({ topic }: { topic: string }) {
  return (
    <Box marginY={1}>
      <Text bold>Topic: {topic}</Text>
    </Box>
  );
}

function DraftNotePanel({
  draft,
  separator,
}: {
  draft: Draft | null;
  separator: string;
}) {
  if (draft === null) {
    return null;
  }

  const hasBody = draft.content.length > 0;

  return (
    <Box flexDirection="column" marginY={1}>
      {draft.topic !== null && (
        <Text>
          <Text color="yellow">Topic: </Text>
          <Text bold>{draft.topic}</Text>
        </Text>
      )}
      {draft.tags.length > 0 && <DraftTags tags={draft.tags} />}
      {hasBody && (
        <Box flexDirection="column" marginTop={1}>
          <Text dimColor>{separator}</Text>
          <Text>{draft.content}</Text>
        </Box>
      )}
    </Box>
  );
}

function DraftTags({ tags }: { tags: { label: string; reused: boolean }[] }) {
  return (
    <Box marginTop={1}>
      <Text>
        <Text dimColor>Tags: </Text>
        {tags.map((tag, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: tags have no stable id
          <Text key={index}>
            {index > 0 && <Text dimColor> · </Text>}
            <Text color="cyan">{tag.label}</Text>
            {!tag.reused && <Text dimColor> (new)</Text>}
          </Text>
        ))}
      </Text>
    </Box>
  );
}

function ApprovedPanel() {
  return (
    <Box marginY={1}>
      <Text color="green">✓ Approved — queued for saving</Text>
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
      <Text color="green">
        ✓ This topic seems well covered — keep going, or wrap up when you're
        ready.
      </Text>
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

function shouldShowWelesBrand(
  terminalRows: number,
  transcript: TranscriptEntry[],
  hasTopic: boolean,
  isStreaming: boolean,
  hasError: boolean,
  hasBanner: boolean,
  hasDraft: boolean,
): boolean {
  const rows = terminalRows > 0 ? terminalRows : DEFAULT_TERMINAL_ROWS;
  const inputBlock = 1;
  const topicBlock = hasTopic ? 2 : 0;
  const errorBlock = hasError ? 2 : 0;
  const bannerBlock = hasBanner ? 2 : 0;
  const draftBlock = hasDraft ? 2 : 0;
  const brandBlock = 3;
  const streamingReserve = isStreaming ? 1 : 0;
  const padding = 1;

  const transcriptBudget = Math.max(
    0,
    rows -
      inputBlock -
      topicBlock -
      errorBlock -
      bannerBlock -
      draftBlock -
      brandBlock -
      streamingReserve -
      padding,
  );
  const usedLines = transcript.length + streamingReserve;

  if (usedLines === 0) {
    return true;
  }

  return usedLines < transcriptBudget;
}

function TranscriptLine({ entry }: { entry: TranscriptEntry }) {
  if (entry.role === "user") {
    return (
      <Text>
        <UserLabel />
        {entry.content}
      </Text>
    );
  }

  return (
    <Text>
      <WelesAgentLabel />
      {entry.content}
    </Text>
  );
}
