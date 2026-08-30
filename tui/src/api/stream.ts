// Hand-declared stream event types are the source of truth for SSE payloads.
// `pnpm generate:api` emits `text/event-stream: unknown` for the messages route
// (openapi-typescript 7.x does not surface FastAPI's itemSchema union) — see
// context/changes/capture-flow-socratic-conversation/plan.md Phase 10.

export type ReplyDeltaEvent = {
  type: "delta";
  text: string;
};

export type ReplyDoneEvent = {
  type: "done";
  messageId: string;
  content: string;
  topic: string;
};

export type ReplyStreamEvent = ReplyDeltaEvent | ReplyDoneEvent;

export async function startCaptureSession(): Promise<{ sessionId: string }> {
  throw new Error("Not implemented");
}

// biome-ignore lint/correctness/useYield: stub until phase 11 implements SSE parsing
export async function* sendMessage(
  _sessionId: string,
  _content: string,
): AsyncGenerator<ReplyStreamEvent> {
  throw new Error("Not implemented");
}
