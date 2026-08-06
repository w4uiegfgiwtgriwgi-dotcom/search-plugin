from __future__ import annotations
import csv
import io
import json
from pathlib import Path
from typing import Any
from .adapters import DEFAULT_ADAPTERS, PlatformAdapter
from .database import Database, loads_json_fields
from .matching import FrameMatcher
from .media_analysis import MediaAnalyzer
from .models import SearchOptions, SearchResult
from .query import expand_query

class LocalApiService:
    def __init__(self, db_path: str | Path = "./.local-data/video-material-finder.sqlite", adapters: dict[str, PlatformAdapter] | None = None):
        self.db = Database(db_path)
        self.adapters = adapters or DEFAULT_ADAPTERS
        self.media_analyzer = MediaAnalyzer(self.db)
        self.frame_matcher = FrameMatcher(self.db)
    def close(self) -> None:
        self.db.close()
    def list_platforms(self) -> list[dict[str, Any]]:
        return [{"platform": name, **adapter.capabilities().__dict__, "session": adapter.check_session()} for name, adapter in self.adapters.items()]
    def create_search_task(self, query: str, platforms: list[str] | None = None, max_results_per_platform: int = 10) -> dict[str, Any]:
        selected = platforms or list(self.adapters.keys())
        expanded = expand_query(query)
        task_id = self.db.execute("""
            INSERT INTO search_tasks (input_type, original_query, expanded_queries_json, selected_platforms_json, filters_json, status, progress, started_at)
            VALUES (?, ?, ?, ?, ?, 'running', 10, CURRENT_TIMESTAMP)
        """, ("text", query, json.dumps(expanded, ensure_ascii=False), json.dumps(selected, ensure_ascii=False), json.dumps({"max_results_per_platform": max_results_per_platform}))).lastrowid
        errors: list[str] = []
        result_count = 0
        options = SearchOptions(platforms=selected, max_results_per_platform=max_results_per_platform)
        for platform in selected:
            adapter = self.adapters.get(platform)
            if not adapter:
                errors.append(f"unknown platform: {platform}")
                continue
            try:
                for result in adapter.search(expanded[0], options):
                    self._insert_result(task_id, result)
                    result_count += 1
            except Exception as exc:
                errors.append(f"{platform}: {exc}")
        status = "completed" if not errors else ("partial_success" if result_count else "failed")
        self.db.execute("UPDATE search_tasks SET status = ?, progress = 100, finished_at = CURRENT_TIMESTAMP, error_summary = ? WHERE id = ?", (status, "; ".join(errors), task_id))
        return self.get_search_task(task_id)
    def get_search_task(self, task_id: int) -> dict[str, Any]:
        task = self.db.query_one("SELECT * FROM search_tasks WHERE id = ?", (task_id,))
        if not task:
            raise KeyError(f"task not found: {task_id}")
        return loads_json_fields(task, ["expanded_queries_json", "selected_platforms_json", "filters_json"])
    def list_results(self, task_id: int) -> list[dict[str, Any]]:
        rows = self.db.query_all("SELECT * FROM search_results WHERE task_id = ? ORDER BY id", (task_id,))
        return [loads_json_fields(row, ["public_metrics_json", "raw_metadata_json"]) for row in rows]
    def create_project(self, name: str, note: str = "") -> dict[str, Any]:
        project_id = self.db.execute("INSERT INTO projects (name, note) VALUES (?, ?)", (name, note)).lastrowid
        return self.get_project(project_id)
    def list_projects(self) -> list[dict[str, Any]]:
        return self.db.query_all("SELECT * FROM projects ORDER BY id")
    def get_project(self, project_id: int) -> dict[str, Any]:
        project = self.db.query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
        if not project:
            raise KeyError(f"project not found: {project_id}")
        return project
    def add_material(self, project_id: int, result_id: int, tags: list[str] | None = None, note: str = "", selected_timestamp_ms: int | None = None) -> dict[str, Any]:
        material_id = self.db.execute("""
            INSERT INTO project_materials (project_id, result_id, selected_timestamp_ms, tags_json, note)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, result_id, selected_timestamp_ms, json.dumps(tags or [], ensure_ascii=False), note)).lastrowid
        return self.get_material(material_id)
    def list_materials(self, project_id: int) -> list[dict[str, Any]]:
        rows = self.db.query_all("""
            SELECT pm.*, sr.title, sr.platform, sr.source_url, sr.cover_url
            FROM project_materials pm JOIN search_results sr ON sr.id = pm.result_id
            WHERE pm.project_id = ? ORDER BY pm.id
        """, (project_id,))
        return [loads_json_fields(row, ["tags_json"]) for row in rows]
    def get_material(self, material_id: int) -> dict[str, Any]:
        row = self.db.query_one("SELECT * FROM project_materials WHERE id = ?", (material_id,))
        if not row:
            raise KeyError(f"material not found: {material_id}")
        return loads_json_fields(row, ["tags_json"])
    def add_frame_match_material(
        self,
        project_id: int,
        match_id: int,
        tags: list[str] | None = None,
        note: str = "",
        review_status: str = "confirmed",
    ) -> dict[str, Any]:
        self.get_project(project_id)
        match = self.get_match(match_id)
        if review_status not in {"confirmed", "pending", "rejected"}:
            raise ValueError("review_status 只能是 confirmed/pending/rejected")
        material_id = self.db.execute("""
            INSERT INTO project_frame_matches (project_id, match_id, selected_timestamp_ms, note, tags_json, review_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, match_id, match["timestamp_ms"], note, json.dumps(tags or [], ensure_ascii=False), review_status)).lastrowid
        return self.get_frame_match_material(material_id)
    def list_frame_match_materials(self, project_id: int) -> list[dict[str, Any]]:
        rows = self.db.query_all("""
            SELECT
              pfm.*,
              fm.query_asset_id,
              fm.candidate_video_path,
              fm.timestamp_ms,
              fm.end_timestamp_ms,
              fm.match_type,
              fm.combined_score,
              fm.local_frame_path,
              ma.source_path AS query_image_path,
              ma.thumbnail_path AS query_thumbnail_path
            FROM project_frame_matches pfm
            JOIN frame_matches fm ON fm.id = pfm.match_id
            JOIN media_assets ma ON ma.id = fm.query_asset_id
            WHERE pfm.project_id = ?
            ORDER BY pfm.id DESC
        """, (project_id,))
        return [loads_json_fields(row, ["tags_json"]) for row in rows]
    def get_frame_match_material(self, material_id: int) -> dict[str, Any]:
        row = self.db.query_one("""
            SELECT
              pfm.*,
              fm.query_asset_id,
              fm.candidate_video_path,
              fm.timestamp_ms,
              fm.end_timestamp_ms,
              fm.match_type,
              fm.combined_score,
              fm.local_frame_path,
              ma.source_path AS query_image_path,
              ma.thumbnail_path AS query_thumbnail_path
            FROM project_frame_matches pfm
            JOIN frame_matches fm ON fm.id = pfm.match_id
            JOIN media_assets ma ON ma.id = fm.query_asset_id
            WHERE pfm.id = ?
        """, (material_id,))
        if not row:
            raise KeyError(f"frame match material not found: {material_id}")
        return loads_json_fields(row, ["tags_json"])
    def list_project_library(self, project_id: int) -> dict[str, Any]:
        self.get_project(project_id)
        search_materials = [
            {
                "source_type": "search_result",
                "material_id": item["id"],
                "title": item["title"],
                "platform": item["platform"],
                "source_url": item["source_url"],
                "cover_url": item["cover_url"],
                "selected_timestamp_ms": item["selected_timestamp_ms"],
                "review_status": item["review_status"],
                "rights_status": item["rights_status"],
                "tags": item["tags_json"],
                "note": item["note"],
                "created_at": item["created_at"],
            }
            for item in self.list_materials(project_id)
        ]
        frame_materials = [
            {
                "source_type": "frame_match",
                "material_id": item["id"],
                "match_id": item["match_id"],
                "title": Path(item["candidate_video_path"]).name,
                "platform": "local-video",
                "source_url": item["candidate_video_path"],
                "cover_url": item["local_frame_path"],
                "selected_timestamp_ms": item["selected_timestamp_ms"],
                "timestamp_ms": item["timestamp_ms"],
                "end_timestamp_ms": item["end_timestamp_ms"],
                "match_type": item["match_type"],
                "combined_score": item["combined_score"],
                "review_status": item["review_status"],
                "rights_status": item["rights_status"],
                "tags": item["tags_json"],
                "note": item["note"],
                "created_at": item["created_at"],
                "query_image_path": item["query_image_path"],
                "query_thumbnail_path": item["query_thumbnail_path"],
                "local_frame_path": item["local_frame_path"],
            }
            for item in self.list_frame_match_materials(project_id)
        ]
        items = sorted([*search_materials, *frame_materials], key=lambda item: item["created_at"], reverse=True)
        return {
            "project_id": project_id,
            "total_count": len(items),
            "search_result_count": len(search_materials),
            "frame_match_count": len(frame_materials),
            "items": items,
        }
    def export_results(self, task_id: int, fmt: str) -> str:
        results = self.list_results(task_id)
        if fmt == "json":
            return json.dumps(results, ensure_ascii=False, indent=2)
        if fmt == "csv":
            output = io.StringIO()
            fields = ["id", "platform", "content_type", "title", "source_url", "author_name", "published_at", "rights_status"]
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader(); writer.writerows(results)
            return output.getvalue()
        if fmt == "md":
            return "# 搜索结果导出\n\n" + "".join(f"- [{item['title']}]({item['source_url']}) - {item['platform']}\n" for item in results)
        raise ValueError(f"unsupported export format: {fmt}")
    def analyze_image(self, image_path: str | Path) -> dict[str, Any]:
        return self.media_analyzer.analyze_image(image_path)
    def analyze_uploaded_image(self, filename: str, data: bytes) -> dict[str, Any]:
        return self.media_analyzer.analyze_uploaded_image(filename, data)
    def get_asset(self, asset_id: int) -> dict[str, Any]:
        return self.media_analyzer.get_asset(asset_id)
    def find_frame_match(
        self,
        query_asset_id: int,
        candidate_video_path: str | Path,
        fps: float = 1.0,
        threshold: float = 0.78,
        refine_fps: float = 4.0,
        refine_window_ms: int = 1000,
    ) -> dict[str, Any]:
        return self.frame_matcher.find_matches(query_asset_id, candidate_video_path, fps, threshold, refine_fps, refine_window_ms)
    def find_batch_frame_matches(
        self,
        query_asset_id: int,
        candidate_video_paths: list[str | Path],
        fps: float = 1.0,
        threshold: float = 0.78,
        refine_fps: float = 4.0,
        refine_window_ms: int = 1000,
        top_k: int = 10,
    ) -> dict[str, Any]:
        return self.frame_matcher.find_batch_matches(query_asset_id, candidate_video_paths, fps, threshold, refine_fps, refine_window_ms, top_k)
    def get_match(self, match_id: int) -> dict[str, Any]:
        return self.frame_matcher.get_match(match_id)
    def _insert_result(self, task_id: int, result: SearchResult) -> int:
        r = result.to_record()
        return self.db.execute("""
            INSERT INTO search_results (task_id, platform, platform_content_id, content_type, title, description, author_name, author_url, source_url, cover_url, published_at, duration_ms, public_metrics_json, matched_query, availability_status, rights_status, raw_metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, r["platform"], r["raw_metadata"].get("platform_content_id"), r["content_type"], r["title"], r["description"], r["author_name"], r["author_url"], r["source_url"], r["cover_url"], r["published_at"], r["duration_ms"], json.dumps({}, ensure_ascii=False), r["matched_query"], r["availability_status"], r["rights_status"], json.dumps(r["raw_metadata"], ensure_ascii=False))).lastrowid
