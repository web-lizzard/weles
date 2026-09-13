import type { InstanceAddress } from "./instance/address.js";
import type { ConfigLocation } from "./instance/configStore.js";

export type StartupDecision =
  | { kind: "ready"; address: InstanceAddress }
  | { kind: "missing"; message: string };

export async function resolveStartup(
  _location: ConfigLocation,
): Promise<StartupDecision> {
  throw new Error("Not implemented");
}
