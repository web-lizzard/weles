import { register, signIn } from "../api/auth.js";
import { setInstanceAddress } from "../api/instance.js";
import type { ConfigLocation } from "../instance/configStore.js";
import { resolveStartup } from "../startup.js";

/**
 * `weles register <email>` and `weles sign-in <email>`.
 *
 * Invariants:
 * - The password never arrives through argv, where it would land in shell
 *   history and process listings, nor through piped stdin. It is read only
 *   through `readSecret`, an interactive no-echo prompt; without a TTY the
 *   command exits 1 before any request.
 * - Both commands act on the configured instance only (`resolveStartup`); an
 *   unconfigured instance fails before any prompt.
 * - Nothing is written to disk. A successful sign-in prints a confirmation
 *   and exits; the token is gone with the process (S-03 keeps it).
 *
 * Exit codes follow `runInstanceCommand`: 0 success, 1 refused or no instance
 * configured, 2 usage.
 */
export type AuthCommandDeps = {
  location: ConfigLocation;
  readSecret: (prompt: string) => Promise<string>;
  out: (line: string) => void;
  err: (line: string) => void;
};

const REGISTER_USAGE = "Usage: weles register <email>";
const SIGN_IN_USAGE = "Usage: weles sign-in <email>";

async function prepareInstance(deps: AuthCommandDeps): Promise<number | null> {
  const decision = await resolveStartup(deps.location);
  if (decision.kind === "missing") {
    deps.err(decision.message);
    return 1;
  }
  setInstanceAddress(decision.address);
  return null;
}

async function readPassword(deps: AuthCommandDeps): Promise<string | number> {
  try {
    return await deps.readSecret("Password: ");
  } catch {
    deps.err("Password prompt requires an interactive terminal.");
    return 1;
  }
}

/** args === [email] else usage (2) -> resolveStartup -> setInstanceAddress ->
 * readSecret("Password: ") -> register. `already_registered` tells the person
 * to sign in instead. */
export async function runRegisterCommand(
  args: string[],
  deps: AuthCommandDeps,
): Promise<number> {
  if (args.length !== 1) {
    deps.err(REGISTER_USAGE);
    return 2;
  }

  const instanceExit = await prepareInstance(deps);
  if (instanceExit !== null) {
    return instanceExit;
  }

  const passwordOrExit = await readPassword(deps);
  if (typeof passwordOrExit === "number") {
    return passwordOrExit;
  }

  const outcome = await register(args[0], passwordOrExit);
  switch (outcome.kind) {
    case "registered":
      deps.out("Account registered.");
      return 0;
    case "already_registered":
      deps.err("This email is already registered. Sign in instead.");
      return 1;
    case "invalid_email":
      deps.err("Invalid email address.");
      return 1;
    case "password_too_short":
      deps.err("Password is too short.");
      return 1;
  }
}

/** args === [email] else usage (2) -> resolveStartup -> setInstanceAddress ->
 * readSecret("Password: ") -> signIn. `invalid_credentials` never says which
 * of email or password was wrong. */
export async function runSignInCommand(
  args: string[],
  deps: AuthCommandDeps,
): Promise<number> {
  if (args.length !== 1) {
    deps.err(SIGN_IN_USAGE);
    return 2;
  }

  const instanceExit = await prepareInstance(deps);
  if (instanceExit !== null) {
    return instanceExit;
  }

  const passwordOrExit = await readPassword(deps);
  if (typeof passwordOrExit === "number") {
    return passwordOrExit;
  }

  const outcome = await signIn(args[0], passwordOrExit);
  switch (outcome.kind) {
    case "signed_in":
      deps.out(`Signed in. Session expires at ${outcome.expiresAt}.`);
      return 0;
    case "invalid_credentials":
      deps.err("Invalid credentials.");
      return 1;
  }
}
