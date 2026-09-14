import { readSignIn } from "./auth/credentialStore.js";
import type { InstanceAddress } from "./instance/address.js";
import type { ConfigLocation } from "./instance/configStore.js";
import { readInstanceAddress } from "./instance/configStore.js";

export type StartupDecision =
  | { kind: "ready"; address: InstanceAddress }
  | { kind: "missing"; message: string };

export type LaunchDecision =
  | { kind: "ready"; address: InstanceAddress }
  | { kind: "missing"; message: string }
  | { kind: "signed_out"; message: string }
  | { kind: "expired"; message: string };

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

export async function resolveLaunch(
  location: ConfigLocation,
  now: Date,
): Promise<LaunchDecision> {
  const startup = await resolveStartup(location);
  if (startup.kind === "missing") {
    return { kind: "missing", message: startup.message };
  }
  const address = startup.address;
  const stored = await readSignIn(location, address);
  if (stored === null) {
    return {
      kind: "signed_out",
      message: `Not signed in to ${address}. Run: weles sign-in <email>`,
    };
  }
  if (Date.parse(stored.expiresAt) <= now.getTime()) {
    return {
      kind: "expired",
      message: `Your sign-in to ${address} has expired. Run: weles sign-in <email>`,
    };
  }
  return { kind: "ready", address };
}
