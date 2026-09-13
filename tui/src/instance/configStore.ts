import type { InstanceAddress } from "./address.js";

export type ConfigLocation = { env: NodeJS.ProcessEnv; homeDir: string };

export function configFilePath(_location: ConfigLocation): string {
  throw new Error("Not implemented");
}

export async function readInstanceAddress(
  _location: ConfigLocation,
): Promise<InstanceAddress | null> {
  throw new Error("Not implemented");
}

export async function writeInstanceAddress(
  _location: ConfigLocation,
  _address: InstanceAddress,
): Promise<void> {
  throw new Error("Not implemented");
}
