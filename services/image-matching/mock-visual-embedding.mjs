import crypto from "node:crypto";

export function createMockVisualEmbeddingProvider(dimensions = 16) {
  return {
    name: "mock-visual-embedding",
    dimensions,
    async embed(input) {
      if (!input || !input.bytes) throw new Error("Embedding input bytes are required");
      const seed = crypto.createHash("sha256").update(input.bytes).digest();
      const vector = Array.from({ length: dimensions }, (_, index) => (seed[index] / 255) * 2 - 1);
      const norm = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0)) || 1;
      return vector.map((value) => Number((value / norm).toFixed(6)));
    }
  };
}

export function cosineSimilarity(a, b) {
  if (a.length !== b.length) throw new Error("Vector dimensions must match");
  const dot = a.reduce((sum, value, index) => sum + value * b[index], 0);
  const normA = Math.sqrt(a.reduce((sum, value) => sum + value * value, 0)) || 1;
  const normB = Math.sqrt(b.reduce((sum, value) => sum + value * value, 0)) || 1;
  return dot / (normA * normB);
}
