import type { InstanceAddress } from "./instance/address.js";
import type { ConfigLocation } from "./instance/configStore.js";
import { readInstanceAddress } from "./instance/configStore.js";

export type StartupDecision =
  | { kind: "ready"; address: InstanceAddress }
  | { kind: "missing"; message: string };

const MISSING_MESSAGE =
  "No Weles instance configured. Run: weles instance set <address>";

export async function resolveStartup(
  location: ConfigLocation,
): Promise<StartupDecision> {
  const stored = await readInstanceAddress(location);
  if (stored === null) {
    return { kind: "missing", message: MISSING_MESSAGE };
  }
  return { kind: "ready", address: stored };
}
