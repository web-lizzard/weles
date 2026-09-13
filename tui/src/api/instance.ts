import type { Client } from "openapi-fetch";
import type { InstanceAddress } from "../instance/address.js";
import type { paths } from "./generated/schema.js";

export class InstanceNotConfiguredError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InstanceNotConfiguredError";
  }
}

export function setInstanceAddress(_address: InstanceAddress): void {
  throw new Error("Not implemented");
}

export function instanceAddress(): InstanceAddress {
  throw new Error("Not implemented");
}

export function getClient(): Client<paths> {
  throw new Error("Not implemented");
}
