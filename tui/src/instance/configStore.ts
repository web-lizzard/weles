import { mkdirSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import {
  type InstanceAddress,
  InvalidInstanceAddressError,
  parseInstanceAddress,
} from "./address.js";

export type ConfigLocation = { env: NodeJS.ProcessEnv; homeDir: string };

export function configFilePath(location: ConfigLocation): string {
  const xdg = location.env.XDG_CONFIG_HOME;
  const base =
    typeof xdg === "string" && xdg.length > 0
      ? xdg
      : join(location.homeDir, ".config");
  const path = join(base, "weles", "config.json");
  try {
    mkdirSync(dirname(path), { recursive: true });
  } catch {
    // Path-only queries (e.g. fake XDG roots in unit tests) must not throw.
  }
  return path;
}

export async function readInstanceAddress(
  location: ConfigLocation,
): Promise<InstanceAddress | null> {
  const path = configFilePath(location);
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
    throw new InvalidInstanceAddressError("config file is not valid JSON");
  }

  if (
    typeof parsed !== "object" ||
    parsed === null ||
    !("instanceAddress" in parsed) ||
    typeof (parsed as { instanceAddress: unknown }).instanceAddress !== "string"
  ) {
    throw new InvalidInstanceAddressError(
      "config file is missing instanceAddress",
    );
  }

  return parseInstanceAddress(
    (parsed as { instanceAddress: string }).instanceAddress,
  );
}

export async function writeInstanceAddress(
  location: ConfigLocation,
  address: InstanceAddress,
): Promise<void> {
  const path = configFilePath(location);
  await mkdir(dirname(path), { recursive: true });
  await writeFile(
    path,
    `${JSON.stringify({ instanceAddress: address }, null, 2)}\n`,
    "utf8",
  );
}
