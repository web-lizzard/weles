import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import type { InstanceAddress } from "../instance/address.js";
import type { ConfigLocation } from "../instance/configStore.js";

export type StoredSignIn = {
  instanceAddress: InstanceAddress;
  token: string;
  expiresAt: string;
};

export function credentialsFilePath(location: ConfigLocation): string {
  const xdg = location.env.XDG_CONFIG_HOME;
  const base =
    typeof xdg === "string" && xdg.length > 0
      ? xdg
      : join(location.homeDir, ".config");
  const path = join(base, "weles", "credentials.json");
  try {
    mkdirSync(dirname(path), { recursive: true });
  } catch {
    // Path-only queries (e.g. fake XDG roots in unit tests) must not throw.
  }
  return path;
}

export async function readSignIn(
  _location: ConfigLocation,
  _address: InstanceAddress,
): Promise<StoredSignIn | null> {
  throw new Error("not implemented");
}

export async function writeSignIn(
  _location: ConfigLocation,
  _signIn: StoredSignIn,
): Promise<void> {
  throw new Error("not implemented");
}

export async function clearSignIn(_location: ConfigLocation): Promise<void> {
  throw new Error("not implemented");
}
