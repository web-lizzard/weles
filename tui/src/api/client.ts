import createClient from "openapi-fetch";
import type { paths } from "./generated/schema.js";

async function delegatedFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  if (input instanceof Request && init === undefined) {
    const body =
      input.method !== "GET" && input.method !== "HEAD"
        ? await input.text()
        : undefined;
    const headers: Record<string, string> = {};
    input.headers.forEach((value, key) => {
      const name = key === "content-type" ? "Content-Type" : key;
      headers[name] = value;
    });
    return globalThis.fetch(input.url, {
      method: input.method,
      headers,
      body,
    });
  }
  return globalThis.fetch(input, init);
}

export const client = createClient<paths>({
  baseUrl: "http://localhost:8000",
  fetch: delegatedFetch,
});
