import { mkdtemp, readFile, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  clearSignIn,
  credentialsFilePath,
  readSignIn,
  type StoredSignIn,
  writeSignIn,
} from "../src/auth/credentialStore";
import { parseInstanceAddress } from "../src/instance/address";

const ADDRESS = parseInstanceAddress("http://localhost:8000");
const OTHER_ADDRESS = parseInstanceAddress("http://127.0.0.1:8000");

const SAMPLE: StoredSignIn = {
  instanceAddress: ADDRESS,
  token: "test-access-token",
  expiresAt: "2026-09-15T12:00:00Z",
};

async function tempConfigHome(): Promise<string> {
  return mkdtemp(join(tmpdir(), "weles-credential-test-"));
}

function locationFor(home: string) {
  return { env: { XDG_CONFIG_HOME: home }, homeDir: "/unused-home" };
}

async function fileMode(path: string): Promise<number> {
  const { mode } = await stat(path);
  return mode & 0o777;
}

describe("credential store", () => {
  async function home(): Promise<string> {
    return tempConfigHome();
  }

  it("writes a sign-in that readSignIn returns for the same instance address", async () => {
    const location = locationFor(await home());
    await writeSignIn(location, SAMPLE);

    expect(await readSignIn(location, ADDRESS)).toEqual(SAMPLE);
  });

  it("stores credentials under XDG_CONFIG_HOME/weles/credentials.json", async () => {
    const configHome = await home();
    const location = locationFor(configHome);
    await writeSignIn(location, SAMPLE);

    const path = credentialsFilePath(location);
    expect(path).toBe(join(configHome, "weles", "credentials.json"));
    const raw = await readFile(path, "utf8");
    expect(JSON.parse(raw)).toEqual(SAMPLE);
  });

  it("leaves the credentials file at mode 0600 after write", async () => {
    const location = locationFor(await home());
    await writeSignIn(location, SAMPLE);

    const path = credentialsFilePath(location);
    expect(await fileMode(path)).toBe(0o600);
  });

  it("chmod 0600 when overwriting a pre-existing 0644 credentials file", async () => {
    const location = locationFor(await home());
    const path = credentialsFilePath(location);
    await writeFile(path, "{}", { mode: 0o644 });
    expect(await fileMode(path)).toBe(0o644);

    await writeSignIn(location, SAMPLE);

    expect(await fileMode(path)).toBe(0o600);
    expect(await readSignIn(location, ADDRESS)).toEqual(SAMPLE);
  });

  it("returns null when readSignIn is asked for a different instance address", async () => {
    const location = locationFor(await home());
    await writeSignIn(location, SAMPLE);

    expect(await readSignIn(location, OTHER_ADDRESS)).toBeNull();
  });

  it("returns null when the credentials file is absent", async () => {
    const location = locationFor(await home());

    expect(await readSignIn(location, ADDRESS)).toBeNull();
  });

  it("returns null when the credentials file is not valid JSON", async () => {
    const location = locationFor(await home());
    const path = credentialsFilePath(location);
    await writeFile(path, "not-json", { mode: 0o600 });

    expect(await readSignIn(location, ADDRESS)).toBeNull();
  });

  it("returns null when a required field is missing", async () => {
    const location = locationFor(await home());
    const path = credentialsFilePath(location);
    await writeFile(
      path,
      JSON.stringify({ instanceAddress: ADDRESS, token: "t" }),
      { mode: 0o600 },
    );

    expect(await readSignIn(location, ADDRESS)).toBeNull();
  });

  it("removes the credentials file on clearSignIn", async () => {
    const location = locationFor(await home());
    await writeSignIn(location, SAMPLE);
    const path = credentialsFilePath(location);

    await clearSignIn(location);

    await expect(stat(path)).rejects.toMatchObject({ code: "ENOENT" });
    expect(await readSignIn(location, ADDRESS)).toBeNull();
  });

  it("treats clearSignIn as a no-op when the file is absent", async () => {
    const location = locationFor(await home());

    await expect(clearSignIn(location)).resolves.toBeUndefined();
  });
});
