import createClient from "openapi-fetch";
import type { paths } from "./generated/schema.js";

export const client = createClient<paths>({
  baseUrl: "http://localhost:8000",
  fetch: (...args) => globalThis.fetch(...args),
});
