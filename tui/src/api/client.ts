export async function delegatedFetch(
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
    const response = await globalThis.fetch(input.url, {
      method: input.method,
      headers,
      body,
    });
    return cloneResponse(response);
  }
  const response = await globalThis.fetch(input, init);
  return cloneResponse(response);
}

function cloneResponse(response: Response): Response {
  if (typeof response.clone === "function") {
    return response.clone();
  }
  return response;
}
