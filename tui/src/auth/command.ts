import type { ConfigLocation } from "../instance/configStore.js";

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

/** args === [email] else usage (2) -> resolveStartup -> setInstanceAddress ->
 * readSecret("Password: ") -> register. `already_registered` tells the person
 * to sign in instead. */
export declare function runRegisterCommand(
  args: string[],
  deps: AuthCommandDeps,
): Promise<number>;

/** args === [email] else usage (2) -> resolveStartup -> setInstanceAddress ->
 * readSecret("Password: ") -> signIn. `invalid_credentials` never says which
 * of email or password was wrong. */
export declare function runSignInCommand(
  args: string[],
  deps: AuthCommandDeps,
): Promise<number>;
