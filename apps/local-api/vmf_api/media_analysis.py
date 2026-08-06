from __future__ import annotations

import hashlib
import json
import mimetypes
import subprocess
from pathlib import Path
from typing import Any

from .database import Database, loads_json_fields

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ANALYSIS_VERSION = "stage2-mock-v1"
EMBEDDING_MODEL = "mock-sha256-16"


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _data_dir() -> Path:
    path = _project_root() / ".local-data" / "stage2"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ffprobe_dimensions(path: Path) -> tuple[int | None, int | None]:
    result = _run([
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(path),
    ])
    if result.returncode != 0:
        return None, None
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    if not streams:
        return None, None
    return streams[0].get("width"), streams[0].get("height")


def _raw_8x8_gray(path: Path) -> bytes:
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            "scale=8:8,format=gray",
            "-f",
            "rawvideo",
            "-",
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0 or len(result.stdout) != 64:
        detail = result.stderr.decode("utf-8", errors="ignore")
        raise ValueError(f"无法解码图片用于 pHash: {detail}")
    return result.stdout


def average_hash(path: Path) -> str:
    raw = _raw_8x8_gray(path)
    avg = sum(raw) / len(raw)
    return "".join("1" if value >= avg else "0" for value in raw)


def hash_similarity(left: str, right: str) -> float:
    if len(left) != len(right):
        raise ValueError("hash length mismatch")
    distance = sum(1 for a, b in zip(left, right) if a != b)
    return 1 - distance / len(left)


def mock_embedding(path: Path, dimensions: int = 16) -> list[float]:
    digest = hashlib.sha256(path.read_bytes()).digest()
    values = [digest[index] / 255 * 2 - 1 for index in range(dimensions)]
    norm = sum(value * value for value in values) ** 0.5 or 1
    return [round(value / norm, 6) for value in values]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimension mismatch")
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = sum(value * value for value in left) ** 0.5 or 1
    norm_right = sum(value * value for value in right) ** 0.5 or 1
    return dot / (norm_left * norm_right)


def mock_ocr(path: Path) -> str:
    stem = path.stem.lower()
    if "air" in stem or "kongtiao" in stem or "空调" in stem:
        return "旧空调"
    if "heat" in stem or "高温" in stem:
        return "极端高温 废墟"
    return "Mock OCR 未识别到明确文字"


def make_thumbnail(path: Path, asset_key: str) -> Path:
    output = _data_dir() / f"{asset_key}-thumbnail.png"
    result = _run([
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(path),
        "-vf",
        "scale=320:-1",
        str(output),
    ])
    if result.returncode != 0:
        raise ValueError(f"生成缩略图失败: {result.stderr}")
    return output


def validate_image(path: Path) -> tuple[str, int]:
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {path}")
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError("仅支持 PNG/JPG/WebP 截图")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("图片文件为空")
    if size > 20 * 1024 * 1024:
        raise ValueError("图片不能超过 20MB")
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return mime_type, size


class MediaAnalyzer:
    def __init__(self, db: Database):
        self.db = db

    def analyze_image(self, image_path: str | Path) -> dict[str, Any]:
        path = Path(image_path).resolve()
        mime_type, size = validate_image(path)
        width, height = _ffprobe_dimensions(path)
        phash = average_hash(path)
        embedding = mock_embedding(path)
        asset_key = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]
        thumbnail = make_thumbnail(path, asset_key)
        ocr_text = mock_ocr(path)
        asset_id = self.db.execute(
            """
            INSERT INTO media_assets (
              kind, source_path, mime_type, size_bytes, width, height, thumbnail_path,
              ocr_text, perceptual_hash, embedding_model, embedding_json, analysis_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "query_image",
                str(path),
                mime_type,
                size,
                width,
                height,
                str(thumbnail),
                ocr_text,
                phash,
                EMBEDDING_MODEL,
                json.dumps(embedding),
                ANALYSIS_VERSION,
            ),
        ).lastrowid
        return self.get_asset(asset_id)

    def get_asset(self, asset_id: int) -> dict[str, Any]:
        asset = self.db.query_one("SELECT * FROM media_assets WHERE id = ?", (asset_id,))
        if not asset:
            raise KeyError(f"asset not found: {asset_id}")
        return loads_json_fields(asset, ["embedding_json"])
