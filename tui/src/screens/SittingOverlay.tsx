import { Box, Text } from "ink";
import type { JSX } from "react";
import { useSittingStore } from "../store/sitting.js";

function renderOpening(): JSX.Element {
  return <Text>opening</Text>;
}

function renderNothingDue(): JSX.Element {
  return <Text>nothing_due</Text>;
}

function renderPresented(): JSX.Element {
  return <Text>presented</Text>;
}

function renderComplete(): JSX.Element {
  return <Text>complete</Text>;
}

function renderError(): JSX.Element {
  return <Text>error</Text>;
}

export default function SittingOverlay(): JSX.Element {
  const phase = useSittingStore((s) => s.phase);

  let body: JSX.Element;
  switch (phase) {
    case "opening":
      body = renderOpening();
      break;
    case "nothing_due":
      body = renderNothingDue();
      break;
    case "presented":
      body = renderPresented();
      break;
    case "complete":
      body = renderComplete();
      break;
    case "error":
      body = renderError();
      break;
  }

  return (
    <Box flexDirection="column" flexGrow={1}>
      {body}
    </Box>
  );
}
