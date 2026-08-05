import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { loadRecordedWebSearch } from "../../services/platform-adapters/web-search/recorded-web-search-adapter.mjs";

test("recorded web search adapter normalizes result fields", async () => {
  const results = await loadRecordedWebSearch(path.resolve("tests/fixtures/web-search-sample.html"));
  assert.equal(results.length, 2);
  assert.equal(results[0].platform, "web-search");
  assert.ok(results[0].title);
  assert.ok(results[0].source_url.startsWith("https://"));
});
