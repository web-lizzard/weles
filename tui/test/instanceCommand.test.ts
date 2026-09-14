import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readSignIn, writeSignIn } from "../src/auth/credentialStore";
import { parseInstanceAddress } from "../src/instance/address";
import { runInstanceCommand } from "../src/instance/command";
import { configFilePath } from "../src/instance/configStore";

async function tempConfigHome(): Promise<string> {
  return mkdtemp(join(tmpdir(), "weles-test-config-"));
}

function depsFor(home: string) {
  const out = vi.fn<(line: string) => void>();
  const err = vi.fn<(line: string) => void>();
  const location = { env: { XDG_CONFIG_HOME: home }, homeDir: "/unused-home" };
  return { out, err, location };
}

describe("runInstanceCommand", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("writes the configured path under XDG_CONFIG_HOME when it is set", () => {
    const location = {
      env: { XDG_CONFIG_HOME: "/xdg/weles" },
      homeDir: "/home/person",
    };
    expect(configFilePath(location)).toBe("/xdg/weles/weles/config.json");
  });

  it("falls back to homeDir/.config when XDG_CONFIG_HOME is unset", () => {
    const location = { env: {}, homeDir: "/home/person" };
    expect(configFilePath(location)).toBe(
      "/home/person/.config/weles/config.json",
    );
  });

  it("prints the stored address and returns 0 when one is configured", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);

    expect(
      await runInstanceCommand(["set", "http://localhost:8000"], {
        location,
        out,
        err,
      }),
    ).toBe(0);

    out.mockClear();
    err.mockClear();

    expect(await runInstanceCommand([], { location, out, err })).toBe(0);
    expect(out).toHaveBeenCalledWith("http://localhost:8000");
    expect(err).not.toHaveBeenCalled();
  });

  it("reports no configured instance on stderr and returns 1 when the store is empty", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);

    expect(await runInstanceCommand([], { location, out, err })).toBe(1);
    expect(out).not.toHaveBeenCalled();
    expect(err).toHaveBeenCalledWith(
      "No Weles instance configured. Run: weles instance set <address>",
    );
  });

  it("persists the normalized address to config.json on set", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);

    expect(
      await runInstanceCommand(["set", "https://host.example/weles/"], {
        location,
        out,
        err,
      }),
    ).toBe(0);

    const raw = await readFile(configFilePath(location), "utf8");
    expect(JSON.parse(raw)).toEqual({
      instanceAddress: "https://host.example/weles",
    });
    expect(out).toHaveBeenCalledWith(
      "Weles instance set to https://host.example/weles. Restart any running Weles TUI to use it.",
    );
  });

  it("clears the stored sign-in when the instance address changes", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);
    const first = parseInstanceAddress("http://localhost:8000");
    const second = parseInstanceAddress("http://127.0.0.1:8000");

    await runInstanceCommand(["set", first], { location, out, err });
    await writeSignIn(location, {
      instanceAddress: first,
      token: "token",
      expiresAt: "2099-01-01T00:00:00Z",
    });
    expect(await readSignIn(location, first)).not.toBeNull();

    out.mockClear();
    expect(
      await runInstanceCommand(["set", second], { location, out, err }),
    ).toBe(0);

    expect(await readSignIn(location, first)).toBeNull();
    expect(await readSignIn(location, second)).toBeNull();
  });

  it("keeps the stored sign-in when set is run with the same address again", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);
    const address = parseInstanceAddress("http://localhost:8000");
    const signIn = {
      instanceAddress: address,
      token: "token",
      expiresAt: "2099-01-01T00:00:00Z",
    };

    await runInstanceCommand(["set", address], { location, out, err });
    await writeSignIn(location, signIn);

    out.mockClear();
    expect(
      await runInstanceCommand(["set", "http://localhost:8000"], {
        location,
        out,
        err,
      }),
    ).toBe(0);

    expect(await readSignIn(location, address)).toEqual(signIn);
  });

  it("replaces a previously stored address when set is run again", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);

    await runInstanceCommand(["set", "http://localhost:8000"], {
      location,
      out,
      err,
    });
    out.mockClear();

    expect(
      await runInstanceCommand(["set", "http://localhost:8999"], {
        location,
        out,
        err,
      }),
    ).toBe(0);

    out.mockClear();
    err.mockClear();
    expect(await runInstanceCommand([], { location, out, err })).toBe(0);
    expect(out).toHaveBeenCalledWith("http://localhost:8999");
  });

  it("leaves the stored value untouched and returns 2 when the address is invalid", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);

    await runInstanceCommand(["set", "http://localhost:8000"], {
      location,
      out,
      err,
    });
    out.mockClear();
    err.mockClear();

    expect(
      await runInstanceCommand(["set", "ftp://bad"], { location, out, err }),
    ).toBe(2);
    expect(err.mock.calls[0]?.[0]).toMatch(/scheme/i);

    out.mockClear();
    err.mockClear();
    expect(await runInstanceCommand([], { location, out, err })).toBe(0);
    expect(out).toHaveBeenCalledWith("http://localhost:8000");
  });

  it("returns 2 with a usage line for an unsupported argument shape", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);

    expect(await runInstanceCommand(["set"], { location, out, err })).toBe(2);
    expect(err.mock.calls[0]?.[0]).toMatch(/usage/i);
    expect(out).not.toHaveBeenCalled();
  });

  it("surfaces InvalidInstanceAddressError when the config file holds an invalid address", async () => {
    const home = await tempConfigHome();
    const { out, err, location } = depsFor(home);
    const path = configFilePath(location);
    await writeFile(
      path,
      JSON.stringify({ instanceAddress: "ftp://stored-bad" }),
      "utf8",
    );

    await expect(
      runInstanceCommand([], { location, out, err }),
    ).rejects.toThrow();
  });
});
