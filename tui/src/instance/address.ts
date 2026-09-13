export type InstanceAddress = string & { readonly __brand: "InstanceAddress" };

export class InvalidInstanceAddressError extends Error {}

export function parseInstanceAddress(_raw: string): InstanceAddress {
  throw new Error("Not implemented");
}
