import { Box, Static, Text } from "ink";
import TextInput from "ink-text-input";
import { useEffect, useState } from "react";
import { type TranscriptEntry, useChatStore } from "../store/chat.js";

function TranscriptLine({ entry }: { entry: TranscriptEntry }) {
  const prefix = entry.role === "user" ? "> " : "  ";
  return (
    <Text>
      {prefix}
      {entry.content}
    </Text>
  );
}

export default function CaptureScreen() {
  const initSession = useChatStore((state) => state.initSession);
  const sendUserMessage = useChatStore((state) => state.sendUserMessage);
  const transcript = useChatStore((state) => state.transcript);
  const currentReply = useChatStore((state) => state.currentReply);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const topic = useChatStore((state) => state.topic);

  const [inputValue, setInputValue] = useState("");

  useEffect(() => {
    void initSession();
  }, [initSession]);

  const handleSubmit = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) {
      return;
    }
    setInputValue("");
    void sendUserMessage(trimmed);
  };

  return (
    <Box flexDirection="column">
      {topic !== null && <Text>Topic: {topic}</Text>}
      <Box flexDirection="column" flexGrow={1}>
        <Static items={transcript}>
          {(entry, index) => <TranscriptLine key={index} entry={entry} />}
        </Static>
        {currentReply.length > 0 && <Text> {currentReply}</Text>}
      </Box>
      <Box>
        <Text>&gt; </Text>
        <TextInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          focus={!isStreaming}
        />
      </Box>
    </Box>
  );
}
