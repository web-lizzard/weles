import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { runRegisterCommand, runSignInCommand } from "../src/auth/command";
import { parseInstanceAddress } from "../src/instance/address";
import { writeInstanceAddress } from "../src/instance/configStore";

const EMAIL = "person@example.com";
const PASSWORD = "long-enough-secret";
const EXPIRES_AT = "2026-09-14T12:00:00Z";

vi.mock("../src/api/auth", () => ({
  register: vi.fn(),
  signIn: vi.fn(),
}));

import { register, signIn } from "../src/api/auth";

async function tempConfigHome(): Promise<string> {
  return mkdtemp(join(tmpdir(), "weles-test-config-"));
}

function depsFor(home: string) {
  const out = vi.fn<(line: string) => void>();
  const err = vi.fn<(line: string) => void>();
  const readSecret = vi.fn<(prompt: string) => Promise<string>>();
  const location = { env: { XDG_CONFIG_HOME: home }, homeDir: "/unused-home" };
  return { out, err, readSecret, location };
}

async function configuredHome(): Promise<string> {
  const home = await tempConfigHome();
  const location = { env: { XDG_CONFIG_HOME: home }, homeDir: "/unused-home" };
  await writeInstanceAddress(
    location,
    parseInstanceAddress("http://localhost:8000"),
  );
  return home;
}

describe("runRegisterCommand", () => {
  afterEach(() => {
    vi.mocked(register).mockReset();
    vi.mocked(signIn).mockReset();
    vi.restoreAllMocks();
  });

  it("returns 2 and prints usage when args are not exactly one email", async () => {
    const home = await configuredHome();
    const { out, err, readSecret, location } = depsFor(home);

    expect(
      await runRegisterCommand([], { location, readSecret, out, err }),
    ).toBe(2);
    expect(err.mock.calls[0]?.[0]).toMatch(/usage/i);
    expect(readSecret).not.toHaveBeenCalled();
    expect(register).not.toHaveBeenCalled();
  });

  it("returns 1 with the resolveStartup message when no instance is configured", async () => {
    const home = await tempConfigHome();
    const { out, err, readSecret, location } = depsFor(home);

    expect(
      await runRegisterCommand([EMAIL], { location, readSecret, out, err }),
    ).toBe(1);
    expect(err).toHaveBeenCalledWith(
      "No Weles instance configured. Run: weles instance set <address>",
    );
    expect(readSecret).not.toHaveBeenCalled();
    expect(register).not.toHaveBeenCalled();
  });

  it("prompts for a password and registers when the instance accepts the account", async () => {
    const home = await configuredHome();
    const { out, err, readSecret, location } = depsFor(home);
    readSecret.mockResolvedValue(PASSWORD);
    vi.mocked(register).mockResolvedValue({ kind: "registered" });

    expect(
      await runRegisterCommand([EMAIL], { location, readSecret, out, err }),
    ).toBe(0);

    expect(readSecret).toHaveBeenCalledWith("Password: ");
    expect(register).toHaveBeenCalledWith(EMAIL, PASSWORD);
    expect(out.mock.calls.some(([line]) => /register/i.test(line))).toBe(true);
    expect(err).not.toHaveBeenCalled();
  });

  it.each([
    ["already_registered", { kind: "already_registered" as const }, /sign in/i],
    ["invalid_email", { kind: "invalid_email" as const }, /invalid/i],
    [
      "password_too_short",
      { kind: "password_too_short" as const },
      /password/i,
    ],
  ] as const)(
    "returns 1 when register yields %s",
    async (_label, outcome, errPattern) => {
      const home = await configuredHome();
      const { out, err, readSecret, location } = depsFor(home);
      readSecret.mockResolvedValue(PASSWORD);
      vi.mocked(register).mockResolvedValue(outcome);

      expect(
        await runRegisterCommand([EMAIL], { location, readSecret, out, err }),
      ).toBe(1);

      expect(err.mock.calls[0]?.[0]).toMatch(errPattern);
      expect(out).not.toHaveBeenCalled();
    },
  );

  it("returns 1 when the password prompt fails (non-interactive stdin)", async () => {
    const home = await configuredHome();
    const { out, err, readSecret, location } = depsFor(home);
    readSecret.mockRejectedValue(new Error("stdin is not a TTY"));

    expect(
      await runRegisterCommand([EMAIL], { location, readSecret, out, err }),
    ).toBe(1);

    expect(register).not.toHaveBeenCalled();
    expect(err).toHaveBeenCalled();
  });
});

describe("runSignInCommand", () => {
  afterEach(() => {
    vi.mocked(register).mockReset();
    vi.mocked(signIn).mockReset();
    vi.restoreAllMocks();
  });

  it("returns 2 and prints usage when args are not exactly one email", async () => {
    const home = await configuredHome();
    const { out, err, readSecret, location } = depsFor(home);

    expect(await runSignInCommand([], { location, readSecret, out, err })).toBe(
      2,
    );
    expect(err.mock.calls[0]?.[0]).toMatch(/usage/i);
    expect(readSecret).not.toHaveBeenCalled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it("returns 1 with the resolveStartup message when no instance is configured", async () => {
    const home = await tempConfigHome();
    const { out, err, readSecret, location } = depsFor(home);

    expect(
      await runSignInCommand([EMAIL], { location, readSecret, out, err }),
    ).toBe(1);
    expect(err).toHaveBeenCalledWith(
      "No Weles instance configured. Run: weles instance set <address>",
    );
    expect(readSecret).not.toHaveBeenCalled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it("prompts for a password and signs in when credentials are accepted", async () => {
    const home = await configuredHome();
    const { out, err, readSecret, location } = depsFor(home);
    readSecret.mockResolvedValue(PASSWORD);
    vi.mocked(signIn).mockResolvedValue({
      kind: "signed_in",
      token: "test-token",
      expiresAt: EXPIRES_AT,
    });

    expect(
      await runSignInCommand([EMAIL], { location, readSecret, out, err }),
    ).toBe(0);

    expect(readSecret).toHaveBeenCalledWith("Password: ");
    expect(signIn).toHaveBeenCalledWith(EMAIL, PASSWORD);
    expect(out.mock.calls.some(([line]) => /sign/i.test(line))).toBe(true);
    expect(err).not.toHaveBeenCalled();
  });

  it("returns 1 without naming email or password when credentials are invalid", async () => {
    const home = await configuredHome();
    const { out, err, readSecret, location } = depsFor(home);
    readSecret.mockResolvedValue("wrong-password");
    vi.mocked(signIn).mockResolvedValue({ kind: "invalid_credentials" });

    expect(
      await runSignInCommand([EMAIL], { location, readSecret, out, err }),
    ).toBe(1);

    const message = String(err.mock.calls[0]?.[0] ?? "");
    expect(message).toMatch(/invalid/i);
    expect(message.toLowerCase()).not.toMatch(/email|password/);
    expect(out).not.toHaveBeenCalled();
  });
});
