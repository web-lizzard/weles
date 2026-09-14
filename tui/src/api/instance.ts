import type { Client } from "openapi-fetch";
import createClient from "openapi-fetch";
import type { InstanceAddress } from "../instance/address.js";
import { delegatedFetch } from "./client.js";
import type { paths } from "./generated/schema.js";

export class InstanceNotConfiguredError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InstanceNotConfiguredError";
  }
}

export type SignInProvider = () => Promise<string | null>;

let configuredAddress: InstanceAddress | undefined;
let memoizedClient: Client<paths> | undefined;
let memoizedForAddress: InstanceAddress | undefined;
let _signInProvider: SignInProvider | undefined;

export function setSignInProvider(provider: SignInProvider): void {
  _signInProvider = provider;
}

export async function authorizationHeaders(): Promise<Record<string, string>> {
  const token = _signInProvider ? await _signInProvider() : null;
  if (token === null) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

export function setInstanceAddress(address: InstanceAddress): void {
  configuredAddress = address;
}

export function instanceAddress(): InstanceAddress {
  if (configuredAddress === undefined) {
    throw new InstanceNotConfiguredError(
      "No Weles instance address configured for this process",
    );
  }
  return configuredAddress;
}

export function getClient(): Client<paths> {
  const address = instanceAddress();
  if (memoizedClient === undefined || memoizedForAddress !== address) {
    const client = createClient<paths>({
      baseUrl: address,
      fetch: delegatedFetch,
    });
    client.use({
      async onRequest({ request }) {
        const token = _signInProvider ? await _signInProvider() : null;
        if (token === null) {
          return undefined;
        }
        const headers = new Headers(request.headers);
        headers.set("Authorization", `Bearer ${token}`);
        return new Request(request, { headers });
      },
    });
    memoizedClient = client;
    memoizedForAddress = address;
  }
  return memoizedClient;
}
