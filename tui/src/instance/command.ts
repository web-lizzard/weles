/**
 * `weles instance` — show or set the backend address in `config.json`.
 *
 * Changing the instance address clears any stored sign-in so a token from one
 * deployment is never sent to another (S-03).
 */

import { clearSignIn } from "../auth/credentialStore.js";
import {
  type InstanceAddress,
  InvalidInstanceAddressError,
  parseInstanceAddress,
} from "./address.js";
import {
  type ConfigLocation,
  readInstanceAddress,
  writeInstanceAddress,
} from "./configStore.js";

export type InstanceCommandDeps = {
  location: ConfigLocation;
  out: (line: string) => void;
  err: (line: string) => void;
};

const USAGE = "Usage: weles instance [set <address>]";

const NOT_CONFIGURED =
  "No Weles instance configured. Run: weles instance set <address>";

export async function runInstanceCommand(
  args: string[],
  deps: InstanceCommandDeps,
): Promise<number> {
  const { location, out, err } = deps;

  if (args.length === 0) {
    const stored = await readInstanceAddress(location);
    if (stored === null) {
      err(NOT_CONFIGURED);
      return 1;
    }
    out(stored);
    return 0;
  }

  if (args.length === 2 && args[0] === "set") {
    let address: InstanceAddress;
    try {
      address = parseInstanceAddress(args[1] ?? "");
    } catch (error) {
      if (error instanceof InvalidInstanceAddressError) {
        err(error.message);
        return 2;
      }
      throw error;
    }

    const previous = await readInstanceAddress(location);
    await writeInstanceAddress(location, address);
    if (previous !== null && previous !== address) {
      await clearSignIn(location);
    }
    out(
      `Weles instance set to ${address}. Restart any running Weles TUI to use it.`,
    );
    return 0;
  }

  err(USAGE);
  return 2;
}
