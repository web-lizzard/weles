import type { ConfigLocation } from "./configStore.js";

export type InstanceCommandDeps = {
  location: ConfigLocation;
  out: (line: string) => void;
  err: (line: string) => void;
};

export async function runInstanceCommand(
  _args: string[],
  _deps: InstanceCommandDeps,
): Promise<number> {
  throw new Error("Not implemented");
}
