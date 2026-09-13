import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { parseInstanceAddress } from "../src/instance/address";
import { writeInstanceAddress } from "../src/instance/configStore";
import { resolveStartup } from "../src/startup";

async function tempConfigHome(): Promise<string> {
  return mkdtemp(join(tmpdir(), "weles-test-config-"));
}

describe("resolveStartup", () => {
  it("returns missing with instructions when no instance is stored", async () => {
    const home = await tempConfigHome();
    const location = {
      env: { XDG_CONFIG_HOME: home },
      homeDir: "/unused-home",
    };

    const decision = await resolveStartup(location);

    expect(decision).toEqual({
      kind: "missing",
      message:
        "No Weles instance configured. Run: weles instance set <address>",
    });
  });

  it("returns ready with the stored address when one is configured", async () => {
    const home = await tempConfigHome();
    const location = {
      env: { XDG_CONFIG_HOME: home },
      homeDir: "/unused-home",
    };
    const address = parseInstanceAddress("https://my.weles.example");
    await writeInstanceAddress(location, address);

    const decision = await resolveStartup(location);

    expect(decision).toEqual({ kind: "ready", address });
  });
});
