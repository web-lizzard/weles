import { describe, expect, it } from "vitest";
import {
  InvalidInstanceAddressError,
  parseInstanceAddress,
} from "../src/instance/address";

describe("parseInstanceAddress", () => {
  it("accepts an https URL and drops a trailing slash on the origin", () => {
    expect(parseInstanceAddress("https://my-instance.example/")).toBe(
      "https://my-instance.example",
    );
  });

  it("accepts an http URL without a trailing slash", () => {
    expect(parseInstanceAddress("http://localhost:8000")).toBe(
      "http://localhost:8000",
    );
  });

  it("keeps a non-root path prefix after normalizing the trailing slash", () => {
    expect(parseInstanceAddress("https://host.example/weles/")).toBe(
      "https://host.example/weles",
    );
  });

  it("rejects a non-http(s) scheme with InvalidInstanceAddressError", () => {
    expect(() => parseInstanceAddress("ftp://example.com")).toThrow(
      InvalidInstanceAddressError,
    );
  });

  it("rejects embedded credentials with InvalidInstanceAddressError", () => {
    expect(() =>
      parseInstanceAddress("https://user:secret@host.example"),
    ).toThrow(InvalidInstanceAddressError);
  });

  it("rejects a query string with InvalidInstanceAddressError", () => {
    expect(() =>
      parseInstanceAddress("https://host.example/api?debug=1"),
    ).toThrow(InvalidInstanceAddressError);
  });

  it("rejects a fragment with InvalidInstanceAddressError", () => {
    expect(() =>
      parseInstanceAddress("https://host.example/path#section"),
    ).toThrow(InvalidInstanceAddressError);
  });

  it("rejects unparseable input with InvalidInstanceAddressError", () => {
    expect(() => parseInstanceAddress("not a url")).toThrow(
      InvalidInstanceAddressError,
    );
  });
});
