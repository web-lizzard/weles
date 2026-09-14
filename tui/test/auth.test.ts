import { afterEach, describe, expect, it, vi } from "vitest";
import { register, signIn } from "../src/api/auth";

const EMAIL = "person@example.com";
const PASSWORD = "long-enough-secret";
const EXPIRES_AT = "2026-09-14T12:00:00Z";
const USER_ID = "00000000-0000-4000-8000-000000000001";

function mockFetchJson(body: unknown, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

describe("auth API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("register returns registered when the instance accepts the account", async () => {
    mockFetchJson({ user_id: USER_ID }, 201);

    await expect(register(EMAIL, PASSWORD)).resolves.toEqual({
      kind: "registered",
    });
  });

  it.each([
    [
      "already_registered",
      EMAIL,
      PASSWORD,
      409,
      { code: "email_already_registered", detail: "Email already registered" },
      { kind: "already_registered" },
    ],
    [
      "invalid_email",
      "not-an-email",
      PASSWORD,
      422,
      { code: "invalid_email_address", detail: "Invalid email address" },
      { kind: "invalid_email" },
    ],
    [
      "password_too_short",
      EMAIL,
      "short",
      422,
      { code: "password_too_short", detail: "Password too short" },
      { kind: "password_too_short" },
    ],
  ] as const)(
    "register returns %s when the backend refuses registration",
    async (_label, email, password, status, body, expected) => {
      mockFetchJson(body, status);

      await expect(register(email, password)).resolves.toEqual(expected);
    },
  );

  it("signIn returns signed_in with expiresAt and omits the access token", async () => {
    mockFetchJson(
      {
        access_token: "secret-token-must-not-leak",
        token_type: "bearer",
        expires_at: EXPIRES_AT,
      },
      200,
    );

    await expect(signIn(EMAIL, PASSWORD)).resolves.toEqual({
      kind: "signed_in",
      expiresAt: EXPIRES_AT,
    });
  });

  it("signIn returns invalid_credentials when the instance refuses the pair", async () => {
    mockFetchJson(
      { code: "invalid_credentials", detail: "Invalid credentials" },
      401,
    );

    await expect(signIn(EMAIL, "wrong-password")).resolves.toEqual({
      kind: "invalid_credentials",
    });
  });

  it("register throws when the response status is unexpected", async () => {
    mockFetchJson({ detail: "boom" }, 500);

    await expect(register(EMAIL, PASSWORD)).rejects.toThrow();
  });
});
