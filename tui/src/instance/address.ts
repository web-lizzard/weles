export type InstanceAddress = string & { readonly __brand: "InstanceAddress" };

export class InvalidInstanceAddressError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidInstanceAddressError";
  }
}

export function parseInstanceAddress(raw: string): InstanceAddress {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new InvalidInstanceAddressError("invalid instance address");
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new InvalidInstanceAddressError(
      "instance address must use http or https scheme",
    );
  }

  if (url.username || url.password) {
    throw new InvalidInstanceAddressError(
      "instance address must not include credentials",
    );
  }

  if (url.search) {
    throw new InvalidInstanceAddressError(
      "instance address must not include a query string",
    );
  }

  if (url.hash) {
    throw new InvalidInstanceAddressError(
      "instance address must not include a fragment",
    );
  }

  let path = url.pathname;
  if (path.endsWith("/") && path.length > 1) {
    path = path.slice(0, -1);
  } else if (path === "/") {
    path = "";
  }

  const normalized = path ? `${url.origin}${path}` : url.origin;
  return normalized as InstanceAddress;
}
