import test from "node:test";
import assert from "node:assert/strict";
import { normalizeUrl } from "../../packages/shared-types/url-normalize.mjs";

test("normalizeUrl removes fragments, lowercases host, and drops tracking params", () => {
  assert.equal(
    normalizeUrl("HTTPS://Example.COM:443/watch?utm_source=x&id=42#title"),
    "https://example.com/watch?id=42"
  );
});
