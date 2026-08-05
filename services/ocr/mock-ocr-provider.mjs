export function createMockOcrProvider() {
  return {
    name: "mock-ocr",
    async recognize(input) {
      if (!input || !input.bytes) throw new Error("OCR input bytes are required");
      return {
        provider: "mock-ocr",
        text: input.hintText ?? "极端高温 废墟 旧空调",
        blocks: [
          { text: input.hintText ?? "极端高温 废墟 旧空调", confidence: 0.99, box: [0, 0, 100, 24] }
        ]
      };
    }
  };
}
