/**
 * Register and sign-in calls against the configured instance.
 *
 * Until S-03 the TUI neither keeps a sign-in nor sends one: `signIn` confirms
 * that the instance accepted the credentials and deliberately does not hand the
 * token back to its caller. S-03 widens this return type when it persists it.
 *
 * A refusal the backend states by code comes back as an outcome, never thrown.
 * Only transport failures and unexpected statuses throw.
 */

export type RegisterOutcome =
  | { kind: "registered" }
  | { kind: "already_registered" }
  | { kind: "invalid_email" }
  | { kind: "password_too_short" };

export type SignInOutcome =
  | { kind: "signed_in"; expiresAt: string }
  | { kind: "invalid_credentials" };

/** POST /auth/register. Maps `email_already_registered`,
 * `invalid_email_address` and `password_too_short` to their outcomes. */
export declare function register(
  email: string,
  password: string,
): Promise<RegisterOutcome>;

/** POST /auth/sign-in. Maps `invalid_credentials` to its outcome; the
 * response's `access_token` is dropped here. */
export declare function signIn(
  email: string,
  password: string,
): Promise<SignInOutcome>;
