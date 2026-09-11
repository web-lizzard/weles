import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/** R1-F1 — generated OpenAPI schema must expose review-sitting routes (plan phase 1). */
describe("generated OpenAPI schema (R1-F1)", () => {
  it("includes the three review-sitting paths", () => {
    const schema = readFileSync("src/api/generated/schema.d.ts", "utf8");
    expect(schema).toContain('"/review-sittings"');
    expect(schema).toContain(
      '"/review-sittings/{sitting_id}/cards/{card_id}/back"',
    );
    expect(schema).toContain(
      '"/review-sittings/{sitting_id}/cards/{card_id}/grade"',
    );
    expect(schema).toContain(
      '"/review-sittings/{sitting_id}/cards/{card_id}/rejection"',
    );
    expect(schema).toContain('"/review-sittings/{sitting_id}/current-card"');
  });
});
