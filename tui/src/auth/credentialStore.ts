import { mkdirSync } from "node:fs";
import { chmod, mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import {
  type InstanceAddress,
  parseInstanceAddress,
} from "../instance/address.js";
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

function parseStoredSignIn(raw: unknown): StoredSignIn | null {
  if (typeof raw !== "object" || raw === null) {
    return null;
  }
  const record = raw as Record<string, unknown>;
  if (
    typeof record.token !== "string" ||
    typeof record.expiresAt !== "string" ||
    typeof record.instanceAddress !== "string"
  ) {
    return null;
  }
  try {
    return {
      instanceAddress: parseInstanceAddress(record.instanceAddress),
      token: record.token,
      expiresAt: record.expiresAt,
    };
  } catch {
    return null;
  }
}

export async function readSignIn(
  location: ConfigLocation,
  address: InstanceAddress,
): Promise<StoredSignIn | null> {
  const path = credentialsFilePath(location);
  let raw: string;
  try {
    raw = await readFile(path, "utf8");
  } catch (error) {
    if (
      error instanceof Error &&
      "code" in error &&
      (error as NodeJS.ErrnoException).code === "ENOENT"
    ) {
      return null;
    }
    throw error;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  const signIn = parseStoredSignIn(parsed);
  if (signIn === null || signIn.instanceAddress !== address) {
    return null;
  }
  return signIn;
}

export async function writeSignIn(
  location: ConfigLocation,
  signIn: StoredSignIn,
): Promise<void> {
  const path = credentialsFilePath(location);
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(signIn)}\n`, { mode: 0o600 });
  await chmod(path, 0o600);
}

export async function clearSignIn(location: ConfigLocation): Promise<void> {
  const path = credentialsFilePath(location);
  try {
    await unlink(path);
  } catch (error) {
    if (
      error instanceof Error &&
      "code" in error &&
      (error as NodeJS.ErrnoException).code === "ENOENT"
    ) {
      return;
    }
    throw error;
  }
}
