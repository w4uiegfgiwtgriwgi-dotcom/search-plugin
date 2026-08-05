import { spawnSync } from "node:child_process";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { averageHash, fixtures, similarityFromHash } from "../../services/image-matching/perceptual-hash.mjs";
import { createMockOcrProvider } from "../../services/ocr/mock-ocr-provider.mjs";
import { createMockVisualEmbeddingProvider, cosineSimilarity } from "../../services/image-matching/mock-visual-embedding.mjs";
import { loadRecordedWebSearch } from "../../services/platform-adapters/web-search/recorded-web-search-adapter.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const artifactsDir = path.join(root, "stage0-artifacts", "ffmpeg-smoke");

function run(command, args, options = {}) {
  return spawnSync(command, args, { encoding: "utf8", shell: false, ...options });
}

function firstLine(result) {
  return `${result.stdout ?? ""}${result.stderr ?? ""}`.split(/\r?\n/)[0] ?? "";
}

function commandVersion(command) {
  const result = run(command, ["-version"]);
  return { ok: result.status === 0, status: result.status, output: firstLine(result) };
}

async function verifyFfmpegFrameExtraction() {
  await fsp.mkdir(artifactsDir, { recursive: true });
  const videoPath = path.join(artifactsDir, "input.mp4");
  const framePath = path.join(artifactsDir, "frame-001.png");

  const makeVideo = run("ffmpeg", [
    "-y",
    "-f", "lavfi",
    "-i", "testsrc=size=64x64:rate=1",
    "-t", "1",
    videoPath
  ]);
  if (makeVideo.status !== 0) {
    return { ok: false, detail: `failed to generate test video: ${firstLine(makeVideo)}` };
  }

  const probe = run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "json", videoPath]);
  if (probe.status !== 0) {
    return { ok: false, detail: `failed to probe test video: ${firstLine(probe)}` };
  }

  const extract = run("ffmpeg", ["-y", "-i", videoPath, "-frames:v", "1", framePath]);
  if (extract.status !== 0) {
    return { ok: false, detail: `failed to extract frame: ${firstLine(extract)}` };
  }

  const frameExists = fs.existsSync(framePath) && fs.statSync(framePath).size > 0;
  return { ok: frameExists, detail: frameExists ? `frame extracted: ${path.relative(root, framePath)}` : "frame file missing or empty" };
}

const checks = [];

for (const command of ["ffmpeg", "ffprobe"]) {
  const result = commandVersion(command);
  checks.push({ name: command, status: result.ok ? "passed" : "failed", detail: result.ok ? result.output : `${command} not found in PATH` });
}

if (checks.find((check) => check.name === "ffmpeg")?.status === "passed" && checks.find((check) => check.name === "ffprobe")?.status === "passed") {
  const extraction = await verifyFfmpegFrameExtraction();
  checks.push({ name: "ffmpeg_frame_extraction", status: extraction.ok ? "passed" : "failed", detail: extraction.detail });
} else {
  checks.push({ name: "ffmpeg_frame_extraction", status: "failed", detail: "ffmpeg or ffprobe unavailable" });
}

const hashA = averageHash(fixtures.brightSquare);
const hashB = averageHash(fixtures.brightSquareCompressed);
const hashC = averageHash(fixtures.darkDiagonal);
checks.push({ name: "perceptual_hash_similar_image", status: similarityFromHash(hashA, hashB) >= 0.95 ? "passed" : "failed", detail: `similarity=${similarityFromHash(hashA, hashB).toFixed(3)}` });
checks.push({ name: "perceptual_hash_different_image", status: similarityFromHash(hashA, hashC) < 0.8 ? "passed" : "failed", detail: `similarity=${similarityFromHash(hashA, hashC).toFixed(3)}` });

const bytes = Buffer.from("stage0 screenshot fixture");
const ocr = createMockOcrProvider();
const ocrResult = await ocr.recognize({ bytes, hintText: "旧空调" });
checks.push({ name: "ocr_provider_mock", status: ocrResult.text.includes("旧空调") ? "passed" : "failed", detail: ocrResult.text });

const embedding = createMockVisualEmbeddingProvider(16);
const vectorA = await embedding.embed({ bytes });
const vectorB = await embedding.embed({ bytes });
checks.push({ name: "visual_embedding_mock", status: vectorA.length === 16 && cosineSimilarity(vectorA, vectorB) > 0.999 ? "passed" : "failed", detail: `dimensions=${vectorA.length}, self_similarity=${cosineSimilarity(vectorA, vectorB).toFixed(3)}` });

const fixturePath = path.join(root, "tests", "fixtures", "web-search-sample.html");
const webResults = await loadRecordedWebSearch(fixturePath);
checks.push({ name: "recorded_web_search_adapter", status: webResults.length === 2 && webResults.every((item) => item.title && item.source_url) ? "passed" : "failed", detail: `results=${webResults.length}` });

const passed = checks.filter((check) => check.status === "passed").length;
const failed = checks.filter((check) => check.status === "failed").length;
const report = { generated_at: new Date().toISOString(), phase: "stage0", summary: { passed, failed }, checks };
console.log(JSON.stringify(report, null, 2));
process.exitCode = failed > 0 ? 1 : 0;
