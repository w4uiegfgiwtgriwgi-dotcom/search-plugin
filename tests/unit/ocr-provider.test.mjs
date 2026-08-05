import test from "node:test";
import assert from "node:assert/strict";
import { createMockOcrProvider } from "../../services/ocr/mock-ocr-provider.mjs";

test("mock OCR provider returns deterministic text blocks", async () => {
  const provider = createMockOcrProvider();
  const result = await provider.recognize({ bytes: Buffer.from("fixture"), hintText: "废墟里的旧空调" });
  assert.equal(result.provider, "mock-ocr");
  assert.match(result.text, /旧空调/);
  assert.equal(result.blocks.length, 1);
});
