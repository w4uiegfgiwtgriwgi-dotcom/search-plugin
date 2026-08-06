from __future__ import annotations

import hashlib
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


def _video_key(video_path: Path) -> str:
    stat = video_path.stat()
    raw = f"{video_path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _fps_label(fps: float) -> str:
    return str(fps).replace(".", "p")


def extract_frames(
    video_path: Path,
    query_asset_id: int,
    fps: float = 1.0,
    start_ms: int = 0,
    duration_ms: int | None = None,
    label: str = "coarse",
) -> list[Path]:
    if fps <= 0:
        raise ValueError("抽帧 fps 必须大于 0")
    video_path = video_path.resolve()
    output_dir = _match_dir() / f"asset-{query_asset_id}" / f"{_video_key(video_path)}-{label}-fps-{_fps_label(fps)}-start-{start_ms}"
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in output_dir.glob("frame-*.png"):
        old_frame.unlink()

    pattern = output_dir / "frame-%04d.png"
    command = ["ffmpeg", "-y", "-v", "error"]
    if start_ms > 0:
        command.extend(["-ss", f"{start_ms / 1000:.3f}"])
    command.extend(["-i", str(video_path)])
    if duration_ms is not None:
        command.extend(["-t", f"{duration_ms / 1000:.3f}"])
    command.extend(["-vf", f"fps={fps}", str(pattern)])

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f"候选视频抽帧失败: {result.stderr}")
    return sorted(output_dir.glob("frame-*.png"))


def timestamp_from_frame_index(index: int, fps: float, start_ms: int = 0) -> int:
    return start_ms + int(index / fps * 1000)


class FrameMatcher:
    def __init__(self, db: Database):
        self.db = db

    def find_matches(
        self,
        query_asset_id: int,
        candidate_video_path: str | Path,
        fps: float = 1.0,
        threshold: float = 0.78,
        refine_fps: float = 4.0,
        refine_window_ms: int = 1000,
    ) -> dict[str, Any]:
        query_asset = self._get_query_asset(query_asset_id)
        video_path = Path(candidate_video_path).resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"候选视频不存在: {video_path}")

        coarse_frames = extract_frames(video_path, query_asset_id, fps, label="coarse")
        if not coarse_frames:
            raise ValueError("候选视频未抽取到任何帧")
        coarse_scores = self._score_frames(query_asset, coarse_frames, fps, start_ms=0)
        coarse_best = max(coarse_scores, key=lambda item: item["combined_score"])

        refined_scores: list[dict[str, Any]] = []
        if refine_fps > fps:
            refine_start_ms = max(0, coarse_best["timestamp_ms"] - refine_window_ms)
            refine_duration_ms = (refine_window_ms * 2) + max(int(1000 / fps), int(1000 / refine_fps))
            refined_frames = extract_frames(
                video_path,
                query_asset_id,
                refine_fps,
                start_ms=refine_start_ms,
                duration_ms=refine_duration_ms,
                label="refine",
            )
            refined_scores = self._score_frames(query_asset, refined_frames, refine_fps, start_ms=refine_start_ms)

        all_scores = [*coarse_scores, *refined_scores]
        best = max(all_scores, key=lambda item: item["combined_score"])
        evidence = {
            "threshold": threshold,
            "frame_count": len(coarse_frames),
            "coarse_frame_count": len(coarse_frames),
            "refined_frame_count": len(refined_scores),
            "coarse_best_timestamp_ms": coarse_best["timestamp_ms"],
            "fps": fps,
            "refine_fps": refine_fps,
            "refine_window_ms": refine_window_ms,
            "top_candidates": [
                {
                    "timestamp_ms": item["timestamp_ms"],
                    "combined_score": item["combined_score"],
                    "phash_score": item["phash_score"],
                    "stage": item["stage"],
                }
                for item in sorted(all_scores, key=lambda item: item["combined_score"], reverse=True)[:5]
            ],
        }
        return self._insert_match(query_asset_id, video_path, best, threshold, evidence)

    def find_batch_matches(
        self,
        query_asset_id: int,
        candidate_video_paths: list[str | Path],
        fps: float = 1.0,
        threshold: float = 0.78,
        refine_fps: float = 4.0,
        refine_window_ms: int = 1000,
        top_k: int = 10,
    ) -> dict[str, Any]:
        paths = [str(path).strip() for path in candidate_video_paths if str(path).strip()]
        if not paths:
            raise ValueError("请至少提供一个候选视频路径")
        if len(paths) > 50:
            raise ValueError("阶段2 Mock Provider 单次最多匹配 50 个候选视频")

        matches: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for raw_path in paths:
            try:
                matches.append(self.find_matches(query_asset_id, raw_path, fps, threshold, refine_fps, refine_window_ms))
            except (FileNotFoundError, KeyError, ValueError) as exc:
                errors.append({"candidate_video_path": raw_path, "error": str(exc)})

        matches.sort(key=lambda item: item["combined_score"], reverse=True)
        return {
            "query_asset_id": query_asset_id,
            "candidate_count": len(paths),
            "match_count": len(matches),
            "error_count": len(errors),
            "matches": matches[:top_k],
            "errors": errors,
        }

    def get_match(self, match_id: int) -> dict[str, Any]:
        match = self.db.query_one("SELECT * FROM frame_matches WHERE id = ?", (match_id,))
        if not match:
            raise KeyError(f"match not found: {match_id}")
        return loads_json_fields(match, ["evidence_json"])

    def _get_query_asset(self, query_asset_id: int) -> dict[str, Any]:
        query_asset = self.db.query_one("SELECT * FROM media_assets WHERE id = ?", (query_asset_id,))
        if not query_asset:
            raise KeyError(f"asset not found: {query_asset_id}")
        return query_asset

    def _score_frames(self, query_asset: dict[str, Any], frames: list[Path], fps: float, start_ms: int) -> list[dict[str, Any]]:
        query_hash = query_asset["perceptual_hash"]
        query_embedding = json.loads(query_asset["embedding_json"])
        scored: list[dict[str, Any]] = []
        for index, frame in enumerate(frames):
            phash_score = hash_similarity(query_hash, average_hash(frame))
            visual_score = cosine_similarity(query_embedding, mock_embedding(frame))
            text_score = 1.0 if query_asset["ocr_text"] and query_asset["ocr_text"] != "Mock OCR 未识别到明确文字" else 0.0
            combined = round((phash_score * 0.7) + (max(visual_score, 0) * 0.2) + (text_score * 0.1), 6)
            scored.append(
                {
                    "frame": frame,
                    "timestamp_ms": timestamp_from_frame_index(index, fps, start_ms),
                    "phash_score": round(phash_score, 6),
                    "visual_score": round(visual_score, 6),
                    "text_score": text_score,
                    "combined_score": combined,
                    "stage": "refine" if start_ms else "coarse",
                }
            )
        return scored

    def _insert_match(
        self,
        query_asset_id: int,
        video_path: Path,
        best: dict[str, Any],
        threshold: float,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
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
                best["timestamp_ms"] + int(1000 / max(evidence["refine_fps"], evidence["fps"])),
                match_type,
                best["phash_score"],
                best["visual_score"],
                best["text_score"],
                best["combined_score"],
                str(best["frame"]),
                json.dumps(evidence, ensure_ascii=False),
            ),
        ).lastrowid
        return self.get_match(match_id)
