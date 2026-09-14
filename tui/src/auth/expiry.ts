export const SIGN_IN_REQUIRED = "sign_in_required";

export const SIGN_IN_EXPIRED_DETAIL =
  "Your sign-in has expired. Run `weles sign-in <email>` in another terminal, then try again.";

export function isSignInRequired(code: string): boolean {
  return code === SIGN_IN_REQUIRED;
}
