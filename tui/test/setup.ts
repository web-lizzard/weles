import { beforeEach } from "vitest";
import { setInstanceAddress } from "../src/api/instance.js";
import { parseInstanceAddress } from "../src/instance/address.js";

const realFetch = globalThis.fetch;
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  const url = input instanceof Request ? input.url : String(input);
  if (url.startsWith("http:") || url.startsWith("https:")) {
    throw new Error(
      `Unmocked fetch to ${url} — mock the src/api/* module boundary instead of hitting the network.`,
    );
  }
  return realFetch(input, init);
}) as typeof fetch;

beforeEach(() => {
  setInstanceAddress(parseInstanceAddress("http://localhost:8000"));
});
