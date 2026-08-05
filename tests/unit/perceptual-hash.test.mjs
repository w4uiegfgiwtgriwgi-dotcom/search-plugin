import test from "node:test";
import assert from "node:assert/strict";
import { averageHash, fixtures, similarityFromHash } from "../../services/image-matching/perceptual-hash.mjs";

test("perceptual hash keeps similar simple images close", () => {
  const original = averageHash(fixtures.brightSquare);
  const compressed = averageHash(fixtures.brightSquareCompressed);
  assert.ok(similarityFromHash(original, compressed) >= 0.95);
});

test("perceptual hash separates obviously different simple images", () => {
  const original = averageHash(fixtures.brightSquare);
  const different = averageHash(fixtures.darkDiagonal);
  assert.ok(similarityFromHash(original, different) < 0.8);
});
