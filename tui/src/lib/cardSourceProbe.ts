import type { CardSource } from "../api/sittings.js";
import { fetchCardSource } from "../api/sittings.js";

const inFlightProbes = new Map<string, Promise<CardSource | null>>();

export function probeCardSource(
  sittingId: string,
  cardId: string,
): Promise<CardSource | null> {
  const key = `${sittingId}\0${cardId}`;
  const existing = inFlightProbes.get(key);
  if (existing !== undefined) {
    return existing;
  }
  const pending = Promise.resolve(fetchCardSource(sittingId, cardId))
    .then((source) => source ?? null)
    .finally(() => {
      inFlightProbes.delete(key);
    });
  inFlightProbes.set(key, pending);
  return pending;
}
