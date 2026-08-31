// Hand-declared stream event types are the source of truth for SSE payloads.
// `pnpm generate:api` emits `text/event-stream: unknown` for the messages route
// (openapi-typescript 7.x does not surface FastAPI's itemSchema union) — see
// context/changes/capture-flow-socratic-conversation/plan.md Phase 10.

import { client } from "./client.js";

const API_BASE_URL = "http://localhost:8000";

export type ReplyDeltaEvent = {
  type: "delta";
  text: string;
};

export type ReplyDoneEvent = {
  type: "done";
  messageId: string;
  content: string;
  topic: string;
  coverageConfidence: number;
};

export type ReplyErrorEvent = {
  type: "error";
  code: string;
  detail: string;
};

export type ReplyStreamEvent =
  | ReplyDeltaEvent
  | ReplyDoneEvent
  | ReplyErrorEvent;

export class SendMessageHttpError extends Error {
  constructor(
    public code: string,
    public detail: string,
    public status: number,
  ) {
    super(detail);
  }
}

export async function startCaptureSession(): Promise<{ sessionId: string }> {
  const { data, error } = await client.POST("/capture-sessions");
  if (error || !data) {
    throw new Error("Failed to start capture session");
  }
  return { sessionId: data.session_id };
}

export async function* sendMessage(
  sessionId: string,
  content: string,
): AsyncGenerator<ReplyStreamEvent> {
  const response = await fetch(
    `${API_BASE_URL}/capture-sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    },
  );

  if (!response.ok) {
    try {
      const body = (await response.json()) as Record<string, unknown>;
      const { code, detail } = body;
      if (typeof code === "string" && typeof detail === "string") {
        throw new SendMessageHttpError(code, detail, response.status);
      }
    } catch (error) {
      if (error instanceof SendMessageHttpError) {
        throw error;
      }
    }
    throw new Error(`sendMessage failed: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Response body is empty");
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();

  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += value;

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) {
        continue;
      }
      const json = line.slice("data:".length).trim();
      yield parseStreamEvent(json);
    }
  }

  const trailing = buffer.trim();
  if (trailing.startsWith("data:")) {
    const json = trailing.slice("data:".length).trim();
    yield parseStreamEvent(json);
  }
}

type RawReplyStreamEvent =
  | { type: "delta"; text: string }
  | {
      type: "done";
      message_id: string;
      content: string;
      topic: string;
      coverage_confidence: number;
    }
  | { type: "error"; code: string; detail: string };

function parseStreamEvent(json: string): ReplyStreamEvent {
  const raw = JSON.parse(json) as RawReplyStreamEvent;
  if (raw.type === "delta") {
    return { type: "delta", text: raw.text };
  }
  if (raw.type === "error") {
    return { type: "error", code: raw.code, detail: raw.detail };
  }
  return {
    type: "done",
    messageId: raw.message_id,
    content: raw.content,
    topic: raw.topic,
    coverageConfidence: raw.coverage_confidence,
  };
}
