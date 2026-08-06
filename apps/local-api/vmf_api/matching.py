from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .database import Database, loads_json_fields
from .media_analysis import average_hash, cosine_similarity, hash_similarity, mock_embedding


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _match_dir() -> Path:
    path = _project_root() / ".local-data" / "stage2" / "matches"
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_frames(video_path: Path, query_asset_id: int, fps: float = 1.0) -> list[Path]:
    output_dir = _match_dir() / f"asset-{query_asset_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame-%04d.png"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
            str(pattern),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"候选视频抽帧失败: {result.stderr}")
    return sorted(output_dir.glob("frame-*.png"))


def timestamp_from_frame_index(index: int, fps: float) -> int:
    return int(index / fps * 1000)


class FrameMatcher:
    def __init__(self, db: Database):
        self.db = db

    def find_matches(self, query_asset_id: int, candidate_video_path: str | Path, fps: float = 1.0, threshold: float = 0.78) -> dict[str, Any]:
        query_asset = self.db.query_one("SELECT * FROM media_assets WHERE id = ?", (query_asset_id,))
        if not query_asset:
            raise KeyError(f"asset not found: {query_asset_id}")
        video_path = Path(candidate_video_path).resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"候选视频不存在: {video_path}")

        query_hash = query_asset["perceptual_hash"]
        query_embedding = json.loads(query_asset["embedding_json"])
        frames = extract_frames(video_path, query_asset_id, fps)
        if not frames:
            raise ValueError("候选视频未抽取到任何帧")

        scored: list[dict[str, Any]] = []
        for index, frame in enumerate(frames):
            phash_score = hash_similarity(query_hash, average_hash(frame))
            visual_score = cosine_similarity(query_embedding, mock_embedding(frame))
            text_score = 1.0 if query_asset["ocr_text"] and query_asset["ocr_text"] != "Mock OCR 未识别到明确文字" else 0.0
            combined = round((phash_score * 0.7) + (max(visual_score, 0) * 0.2) + (text_score * 0.1), 6)
            scored.append(
                {
                    "frame": frame,
                    "timestamp_ms": timestamp_from_frame_index(index, fps),
                    "phash_score": round(phash_score, 6),
                    "visual_score": round(visual_score, 6),
                    "text_score": text_score,
                    "combined_score": combined,
                }
            )

        best = max(scored, key=lambda item: item["combined_score"])
        match_type = "same_frame" if best["combined_score"] >= 0.92 else ("visually_similar" if best["combined_score"] >= threshold else "unreliable")
        match_id = self.db.execute(
            """
            INSERT INTO frame_matches (
              query_asset_id, candidate_video_path, timestamp_ms, end_timestamp_ms,
              match_type, phash_score, visual_score, text_score, combined_score,
              local_frame_path, evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_asset_id,
                str(video_path),
                best["timestamp_ms"],
                best["timestamp_ms"] + int(1000 / fps),
                match_type,
                best["phash_score"],
                best["visual_score"],
                best["text_score"],
                best["combined_score"],
                str(best["frame"]),
                json.dumps({"threshold": threshold, "frame_count": len(frames)}, ensure_ascii=False),
            ),
        ).lastrowid
        return self.get_match(match_id)

    def get_match(self, match_id: int) -> dict[str, Any]:
        match = self.db.query_one("SELECT * FROM frame_matches WHERE id = ?", (match_id,))
        if not match:
            raise KeyError(f"match not found: {match_id}")
        return loads_json_fields(match, ["evidence_json"])
