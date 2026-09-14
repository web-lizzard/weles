import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { writeSignIn } from "../src/auth/credentialStore";
import { parseInstanceAddress } from "../src/instance/address";
import { writeInstanceAddress } from "../src/instance/configStore";
import { resolveLaunch } from "../src/startup";

const ADDRESS = parseInstanceAddress("http://localhost:8000");

async function tempConfigHome(): Promise<string> {
  return mkdtemp(join(tmpdir(), "weles-launch-test-"));
}

function locationFor(home: string) {
  return { env: { XDG_CONFIG_HOME: home }, homeDir: "/unused-home" };
}

describe("resolveLaunch", () => {
  it("returns missing with instructions when no instance is stored", async () => {
    const location = locationFor(await tempConfigHome());

    const decision = await resolveLaunch(
      location,
      new Date("2026-09-14T12:00:00Z"),
    );

    expect(decision).toEqual({
      kind: "missing",
      message:
        "No Weles instance configured. Run: weles instance set <address>",
    });
  });

  it("returns signed_out when an address is configured but no credential exists", async () => {
    const location = locationFor(await tempConfigHome());
    await writeInstanceAddress(location, ADDRESS);

    const decision = await resolveLaunch(
      location,
      new Date("2026-09-14T12:00:00Z"),
    );

    expect(decision).toEqual({
      kind: "signed_out",
      message:
        "Not signed in to http://localhost:8000. Run: weles sign-in <email>",
    });
  });

  it("returns expired when the stored sign-in expires at or before now", async () => {
    const location = locationFor(await tempConfigHome());
    await writeInstanceAddress(location, ADDRESS);
    await writeSignIn(location, {
      instanceAddress: ADDRESS,
      token: "token",
      expiresAt: "2026-09-14T12:00:00Z",
    });

    const decision = await resolveLaunch(
      location,
      new Date("2026-09-14T12:00:00Z"),
    );

    expect(decision).toEqual({
      kind: "expired",
      message:
        "Your sign-in to http://localhost:8000 has expired. Run: weles sign-in <email>",
    });
  });

  it("returns ready when the stored sign-in expires after now", async () => {
    const location = locationFor(await tempConfigHome());
    await writeInstanceAddress(location, ADDRESS);
    await writeSignIn(location, {
      instanceAddress: ADDRESS,
      token: "token",
      expiresAt: "2026-09-15T12:00:00Z",
    });

    const decision = await resolveLaunch(
      location,
      new Date("2026-09-14T12:00:00Z"),
    );

    expect(decision).toEqual({ kind: "ready", address: ADDRESS });
  });
});
