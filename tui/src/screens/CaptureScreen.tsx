import { Box, Text } from "ink";

export default function CaptureScreen() {
  return (
    <Box flexDirection="column">
      <Box flexDirection="column" flexGrow={1}>
        <Text dimColor>Transcript</Text>
      </Box>
      <Box>
        <Text dimColor>&gt; </Text>
        <Text dimColor>Input</Text>
      </Box>
    </Box>
  );
}
