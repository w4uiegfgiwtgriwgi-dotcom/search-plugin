import test from "node:test";
import assert from "node:assert/strict";
import { createMockVisualEmbeddingProvider, cosineSimilarity } from "../../services/image-matching/mock-visual-embedding.mjs";

test("mock visual embedding provider returns normalized deterministic vectors", async () => {
  const provider = createMockVisualEmbeddingProvider(16);
  const first = await provider.embed({ bytes: Buffer.from("same") });
  const second = await provider.embed({ bytes: Buffer.from("same") });
  assert.equal(first.length, 16);
  assert.ok(cosineSimilarity(first, second) > 0.999);
});
