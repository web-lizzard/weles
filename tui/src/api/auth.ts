/**
 * Register and sign-in calls against the configured instance.
 *
 * `signIn` confirms that the instance accepted the credentials and returns the
 * access token so the sign-in command can store it in `credentials.json`
 * (S-03). Authorized requests read that file per call via the sign-in provider.
 *
 * A refusal the backend states by code comes back as an outcome, never thrown.
 * Only transport failures and unexpected statuses throw.
 */

import { getClient } from "./instance.js";

export type RegisterOutcome =
  | { kind: "registered" }
  | { kind: "already_registered" }
  | { kind: "invalid_email" }
  | { kind: "password_too_short" };

export type SignInOutcome =
  | { kind: "signed_in"; token: string; expiresAt: string }
  | { kind: "invalid_credentials" };

type CodedErrorBody = { code?: string; detail?: string };

function errorCode(error: unknown): string | undefined {
  const body = error as CodedErrorBody | undefined;
  if (body && typeof body.code === "string") {
    return body.code;
  }
  return undefined;
}

/** POST /auth/register. Maps `email_already_registered`,
 * `invalid_email_address` and `password_too_short` to their outcomes. */
export async function register(
  email: string,
  password: string,
): Promise<RegisterOutcome> {
  const { data, error, response } = await getClient().POST("/auth/register", {
    body: { email, password },
  });
  if (response.status === 201 && data) {
    return { kind: "registered" };
  }
  const code = errorCode(error);
  if (response.status === 409 && code === "email_already_registered") {
    return { kind: "already_registered" };
  }
  if (response.status === 422 && code === "invalid_email_address") {
    return { kind: "invalid_email" };
  }
  if (response.status === 422 && code === "password_too_short") {
    return { kind: "password_too_short" };
  }
  throw new Error(`register failed: ${response.status}`);
}

/** POST /auth/sign-in. Maps `invalid_credentials` to its outcome. */
export async function signIn(
  email: string,
  password: string,
): Promise<SignInOutcome> {
  const { data, error, response } = await getClient().POST("/auth/sign-in", {
    body: { email, password },
  });
  if (response.status === 200 && data) {
    return {
      kind: "signed_in",
      token: data.access_token,
      expiresAt: data.expires_at,
    };
  }
  const code = errorCode(error);
  if (response.status === 401 && code === "invalid_credentials") {
    return { kind: "invalid_credentials" };
  }
  throw new Error(`signIn failed: ${response.status}`);
}
