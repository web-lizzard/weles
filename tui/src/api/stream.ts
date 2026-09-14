// Hand-declared stream event types are the source of truth for SSE payloads.
// `pnpm generate:api` emits `text/event-stream: unknown` for the messages route
// (openapi-typescript 7.x does not surface FastAPI's itemSchema union) — see
// context/changes/capture-flow-socratic-conversation/plan.md Phase 10.

import {
  authorizationHeaders,
  getClient,
  instanceAddress,
} from "./instance.js";

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

export type DraftTopicEvent = {
  type: "draft_topic";
  label: string;
  reused: boolean;
};

export type DraftTagEvent = {
  type: "draft_tag";
  label: string;
  reused: boolean;
};

export type DraftDeltaEvent = {
  type: "draft_delta";
  text: string;
};

export type DraftDoneEvent = {
  type: "draft_done";
  noteId: string;
  topic: string;
  content: string;
  tags: string[];
};

export type ReplyStreamEvent =
  | ReplyDeltaEvent
  | ReplyDoneEvent
  | ReplyErrorEvent
  | DraftTopicEvent
  | DraftTagEvent
  | DraftDeltaEvent
  | DraftDoneEvent;

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
  const { data, error, response } = await getClient().POST("/capture-sessions");
  if (error || !data) {
    const body = error as { code?: string; detail?: string } | undefined;
    if (
      body &&
      typeof body.code === "string" &&
      typeof body.detail === "string"
    ) {
      throw new SendMessageHttpError(
        body.code,
        body.detail,
        (response as Response).status,
      );
    }
    throw new Error("Failed to start capture session");
  }
  return { sessionId: data.session_id };
}

export async function approveNote(
  sessionId: string,
): Promise<{ noteId: string; topic: string; tags: string[] }> {
  const { data, error, response } = await getClient().POST(
    "/capture-sessions/{session_id}/approval",
    { params: { path: { session_id: sessionId } } },
  );
  if (error || !data) {
    const body = error as { code?: string; detail?: string } | undefined;
    if (
      body &&
      typeof body.code === "string" &&
      typeof body.detail === "string"
    ) {
      throw new SendMessageHttpError(
        body.code,
        body.detail,
        (response as Response).status,
      );
    }
    throw new Error(`approveNote failed: ${response.status}`);
  }
  return { noteId: data.note_id, topic: data.topic, tags: data.tags };
}

export async function* sendMessage(
  sessionId: string,
  content: string,
): AsyncGenerator<ReplyStreamEvent> {
  const authHeaders = await authorizationHeaders();
  const response = await fetch(
    `${instanceAddress()}/capture-sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
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
  | { type: "error"; code: string; detail: string }
  | { type: "draft_topic"; label: string; reused: boolean }
  | { type: "draft_tag"; label: string; reused: boolean }
  | { type: "draft_delta"; text: string }
  | {
      type: "draft_done";
      note_id: string;
      topic: string;
      content: string;
      tags: string[];
    };

function parseStreamEvent(json: string): ReplyStreamEvent {
  const raw = JSON.parse(json) as RawReplyStreamEvent;
  if (raw.type === "delta") {
    return { type: "delta", text: raw.text };
  }
  if (raw.type === "error") {
    return { type: "error", code: raw.code, detail: raw.detail };
  }
  if (raw.type === "done") {
    return {
      type: "done",
      messageId: raw.message_id,
      content: raw.content,
      topic: raw.topic,
      coverageConfidence: raw.coverage_confidence,
    };
  }
  if (raw.type === "draft_topic") {
    return { type: "draft_topic", label: raw.label, reused: raw.reused };
  }
  if (raw.type === "draft_tag") {
    return { type: "draft_tag", label: raw.label, reused: raw.reused };
  }
  if (raw.type === "draft_delta") {
    return { type: "draft_delta", text: raw.text };
  }
  if (raw.type === "draft_done") {
    return {
      type: "draft_done",
      noteId: raw.note_id,
      topic: raw.topic,
      content: raw.content,
      tags: raw.tags,
    };
  }
  throw new Error(
    `Unimplemented stream event type: ${(raw as { type: string }).type}`,
  );
}
