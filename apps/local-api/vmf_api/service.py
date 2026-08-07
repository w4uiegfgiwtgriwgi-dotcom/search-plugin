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
    REVIEW_STATUSES = {"confirmed", "pending", "rejected"}
    RIGHTS_STATUSES = {"unknown", "cleared", "needs_permission", "blocked"}
    MAX_MATERIAL_TAGS = 20
    MAX_MATERIAL_TAG_LENGTH = 40
    MAX_MATERIAL_NOTE_LENGTH = 1000

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
        self.get_project(project_id)
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
    def update_material_review_status(
        self,
        project_id: int,
        source_type: str,
        material_id: int,
        review_status: str,
    ) -> dict[str, Any]:
        self.get_project(project_id)
        if review_status not in self.REVIEW_STATUSES:
            raise ValueError("review_status 只能是 confirmed/pending/rejected")
        if source_type == "search_result":
            existing = self.db.query_one(
                "SELECT id FROM project_materials WHERE id = ? AND project_id = ?",
                (material_id, project_id),
            )
            if not existing:
                raise KeyError(f"material not found: {material_id}")
            self.db.execute(
                "UPDATE project_materials SET review_status = ? WHERE id = ? AND project_id = ?",
                (review_status, material_id, project_id),
            )
        elif source_type == "frame_match":
            existing = self.db.query_one(
                "SELECT id FROM project_frame_matches WHERE id = ? AND project_id = ?",
                (material_id, project_id),
            )
            if not existing:
                raise KeyError(f"frame match material not found: {material_id}")
            self.db.execute(
                "UPDATE project_frame_matches SET review_status = ? WHERE id = ? AND project_id = ?",
                (review_status, material_id, project_id),
            )
        else:
            raise ValueError("source_type 只能是 search_result/frame_match")
        return {
            "project_id": project_id,
            "source_type": source_type,
            "material_id": material_id,
            "review_status": review_status,
        }
    def update_material_metadata(
        self,
        project_id: int,
        source_type: str,
        material_id: int,
        tags: list[str] | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        self.get_project(project_id)
        normalized_tags = self._normalize_material_tags(tags or [])
        normalized_note = self._normalize_material_note(note)
        tags_json = json.dumps(normalized_tags, ensure_ascii=False)
        if source_type == "search_result":
            existing = self.db.query_one(
                "SELECT id FROM project_materials WHERE id = ? AND project_id = ?",
                (material_id, project_id),
            )
            if not existing:
                raise KeyError(f"material not found: {material_id}")
            self.db.execute(
                "UPDATE project_materials SET tags_json = ?, note = ? WHERE id = ? AND project_id = ?",
                (tags_json, normalized_note, material_id, project_id),
            )
        elif source_type == "frame_match":
            existing = self.db.query_one(
                "SELECT id FROM project_frame_matches WHERE id = ? AND project_id = ?",
                (material_id, project_id),
            )
            if not existing:
                raise KeyError(f"frame match material not found: {material_id}")
            self.db.execute(
                "UPDATE project_frame_matches SET tags_json = ?, note = ? WHERE id = ? AND project_id = ?",
                (tags_json, normalized_note, material_id, project_id),
            )
        else:
            raise ValueError("source_type 只能是 search_result/frame_match")
        return {
            "project_id": project_id,
            "source_type": source_type,
            "material_id": material_id,
            "tags": normalized_tags,
            "note": normalized_note,
        }
    def update_material_rights_status(
        self,
        project_id: int,
        source_type: str,
        material_id: int,
        rights_status: str,
    ) -> dict[str, Any]:
        self.get_project(project_id)
        if rights_status not in self.RIGHTS_STATUSES:
            raise ValueError("rights_status 只能是 unknown/cleared/needs_permission/blocked")
        if source_type == "search_result":
            existing = self.db.query_one(
                "SELECT id FROM project_materials WHERE id = ? AND project_id = ?",
                (material_id, project_id),
            )
            if not existing:
                raise KeyError(f"material not found: {material_id}")
            self.db.execute(
                "UPDATE project_materials SET rights_status = ? WHERE id = ? AND project_id = ?",
                (rights_status, material_id, project_id),
            )
        elif source_type == "frame_match":
            existing = self.db.query_one(
                "SELECT id FROM project_frame_matches WHERE id = ? AND project_id = ?",
                (material_id, project_id),
            )
            if not existing:
                raise KeyError(f"frame match material not found: {material_id}")
            self.db.execute(
                "UPDATE project_frame_matches SET rights_status = ? WHERE id = ? AND project_id = ?",
                (rights_status, material_id, project_id),
            )
        else:
            raise ValueError("source_type 只能是 search_result/frame_match")
        return {
            "project_id": project_id,
            "source_type": source_type,
            "material_id": material_id,
            "rights_status": rights_status,
        }
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
        if review_status not in self.REVIEW_STATUSES:
            raise ValueError("review_status 只能是 confirmed/pending/rejected")
        material_id = self.db.execute("""
            INSERT INTO project_frame_matches (project_id, match_id, selected_timestamp_ms, note, tags_json, review_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, match_id, match["timestamp_ms"], note, json.dumps(tags or [], ensure_ascii=False), review_status)).lastrowid
        return self.get_frame_match_material(material_id)
    def add_frame_match_materials(
        self,
        project_id: int,
        match_ids: list[int],
        min_score: float = 0.75,
        tags: list[str] | None = None,
        note: str = "",
        review_status: str = "confirmed",
    ) -> dict[str, Any]:
        self.get_project(project_id)
        if not match_ids:
            raise ValueError("请至少提供一个匹配结果")
        if len(match_ids) > 100:
            raise ValueError("单次最多收藏 100 个匹配结果")
        saved: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for match_id in match_ids:
            try:
                match = self.get_match(int(match_id))
                if float(match["combined_score"]) < min_score:
                    skipped.append({"match_id": int(match_id), "reason": "below_min_score", "combined_score": match["combined_score"]})
                    continue
                existing = self.db.query_one(
                    "SELECT id FROM project_frame_matches WHERE project_id = ? AND match_id = ?",
                    (project_id, int(match_id)),
                )
                if existing:
                    skipped.append({"match_id": int(match_id), "reason": "already_saved", "material_id": existing["id"]})
                    continue
                saved.append(self.add_frame_match_material(project_id, int(match_id), tags, note, review_status))
            except (KeyError, ValueError) as exc:
                errors.append({"match_id": str(match_id), "error": str(exc)})
        return {
            "project_id": project_id,
            "requested_count": len(match_ids),
            "saved_count": len(saved),
            "skipped_count": len(skipped),
            "error_count": len(errors),
            "saved": saved,
            "skipped": skipped,
            "errors": errors,
        }
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
    def list_project_library(
        self,
        project_id: int,
        source_type: str | None = None,
        review_status: str | None = None,
        rights_status: str | None = None,
        keyword: str | None = None,
        sort_by: str = "created_desc",
    ) -> dict[str, Any]:
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
        all_items = [*search_materials, *frame_materials]
        items = list(all_items)
        if source_type and source_type != "all":
            if source_type not in {"search_result", "frame_match"}:
                raise ValueError("source_type 只能是 all/search_result/frame_match")
            items = [item for item in items if item["source_type"] == source_type]
        if review_status and review_status != "all":
            items = [item for item in items if item["review_status"] == review_status]
        if rights_status and rights_status != "all":
            if rights_status not in self.RIGHTS_STATUSES:
                raise ValueError("rights_status 只能是 all/unknown/cleared/needs_permission/blocked")
            items = [item for item in items if item["rights_status"] == rights_status]
        normalized_keyword = (keyword or "").strip().lower()
        if normalized_keyword:
            items = [item for item in items if self._library_item_matches_keyword(item, normalized_keyword)]
        if sort_by == "created_asc":
            items = sorted(items, key=lambda item: item["created_at"])
        elif sort_by == "score_desc":
            items = sorted(items, key=lambda item: item.get("combined_score") or -1, reverse=True)
        elif sort_by == "title_asc":
            items = sorted(items, key=lambda item: item["title"])
        elif sort_by == "created_desc":
            items = sorted(items, key=lambda item: item["created_at"], reverse=True)
        else:
            raise ValueError("sort_by 只能是 created_desc/created_asc/score_desc/title_asc")
        return {
            "project_id": project_id,
            "total_count": len(items),
            "search_result_count": sum(1 for item in items if item["source_type"] == "search_result"),
            "frame_match_count": sum(1 for item in items if item["source_type"] == "frame_match"),
            "summary": self._build_library_summary(all_items, items),
            "items": items,
        }
    def export_project_library(
        self,
        project_id: int,
        fmt: str,
        source_type: str | None = None,
        review_status: str | None = None,
        rights_status: str | None = None,
        keyword: str | None = None,
        sort_by: str = "created_desc",
    ) -> str:
        library = self.list_project_library(project_id, source_type, review_status, rights_status, keyword, sort_by)
        items = library["items"]
        if fmt == "json":
            return json.dumps(library, ensure_ascii=False, indent=2)
        if fmt == "csv":
            output = io.StringIO()
            fields = [
                "source_type",
                "material_id",
                "title",
                "platform",
                "source_url",
                "selected_timestamp_ms",
                "combined_score",
                "review_status",
                "rights_status",
                "tags",
                "note",
                "created_at",
            ]
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                copied = dict(item)
                copied["tags"] = " / ".join(copied.get("tags") or [])
                writer.writerow(copied)
            return output.getvalue()
        if fmt == "md":
            lines = [f"# 项目 {project_id} 素材库", ""]
            for item in items:
                tags = " / ".join(item.get("tags") or []) or "未打标签"
                lines.append(f"- **{item['title']}** ({item['source_type']})")
                lines.append(f"  - 来源：{item['source_url']}")
                lines.append(f"  - 状态：{item['review_status']}，标签：{tags}")
                if item.get("selected_timestamp_ms") is not None:
                    lines.append(f"  - 时间点：{item['selected_timestamp_ms']}ms")
                if item.get("combined_score") is not None:
                    lines.append(f"  - 匹配分：{item['combined_score']}")
                if item.get("note"):
                    lines.append(f"  - 备注：{item['note']}")
            return "\n".join(lines) + "\n"
        raise ValueError(f"unsupported export format: {fmt}")
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
    def analyze_uploaded_images(self, uploads: list[tuple[str, bytes]]) -> dict[str, Any]:
        if not uploads:
            raise ValueError("请至少上传一张截图")
        if len(uploads) > 20:
            raise ValueError("阶段2单次最多上传 20 张截图")
        assets: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for filename, data in uploads:
            try:
                assets.append(self.analyze_uploaded_image(filename, data))
            except ValueError as exc:
                errors.append({"filename": filename, "error": str(exc)})
        return {
            "upload_count": len(uploads),
            "asset_count": len(assets),
            "error_count": len(errors),
            "assets": assets,
            "errors": errors,
        }
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
    def find_multi_asset_frame_matches(
        self,
        query_asset_ids: list[int],
        candidate_video_paths: list[str | Path],
        fps: float = 1.0,
        threshold: float = 0.78,
        refine_fps: float = 4.0,
        refine_window_ms: int = 1000,
        top_k: int = 10,
    ) -> dict[str, Any]:
        asset_ids = [int(asset_id) for asset_id in query_asset_ids]
        if not asset_ids:
            raise ValueError("请至少提供一张已分析截图")
        if len(asset_ids) > 20:
            raise ValueError("阶段2单次最多匹配 20 张截图")
        batches: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for asset_id in asset_ids:
            try:
                batches.append(self.find_batch_frame_matches(asset_id, candidate_video_paths, fps, threshold, refine_fps, refine_window_ms, top_k))
            except (KeyError, ValueError) as exc:
                errors.append({"query_asset_id": str(asset_id), "error": str(exc)})
        best_matches = [batch["matches"][0] for batch in batches if batch["matches"]]
        best_matches.sort(key=lambda item: item["combined_score"], reverse=True)
        return {
            "asset_count": len(asset_ids),
            "batch_count": len(batches),
            "error_count": len(errors),
            "batches": batches,
            "best_matches": best_matches[:top_k],
            "errors": errors,
        }
    def get_match(self, match_id: int) -> dict[str, Any]:
        return self.frame_matcher.get_match(match_id)
    def _normalize_material_tags(self, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            cleaned = str(tag).strip()
            if not cleaned:
                continue
            if len(cleaned) > self.MAX_MATERIAL_TAG_LENGTH:
                raise ValueError(f"标签不能超过 {self.MAX_MATERIAL_TAG_LENGTH} 个字符")
            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        if len(normalized) > self.MAX_MATERIAL_TAGS:
            raise ValueError(f"标签不能超过 {self.MAX_MATERIAL_TAGS} 个")
        return normalized
    def _normalize_material_note(self, note: str) -> str:
        normalized = str(note).strip()
        if len(normalized) > self.MAX_MATERIAL_NOTE_LENGTH:
            raise ValueError(f"备注不能超过 {self.MAX_MATERIAL_NOTE_LENGTH} 个字符")
        return normalized
    def _build_library_summary(self, all_items: list[dict[str, Any]], filtered_items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "all_count": len(all_items),
            "filtered_count": len(filtered_items),
            "by_source_type": {
                "search_result": self._count_library_items(all_items, "source_type", "search_result"),
                "frame_match": self._count_library_items(all_items, "source_type", "frame_match"),
            },
            "by_review_status": {
                status: self._count_library_items(all_items, "review_status", status)
                for status in sorted(self.REVIEW_STATUSES)
            },
            "by_rights_status": {
                status: self._count_library_items(all_items, "rights_status", status)
                for status in sorted(self.RIGHTS_STATUSES)
            },
        }
    def _count_library_items(self, items: list[dict[str, Any]], key: str, value: str) -> int:
        return sum(1 for item in items if item.get(key) == value)
    def _library_item_matches_keyword(self, item: dict[str, Any], keyword: str) -> bool:
        searchable_parts = [
            item.get("title"),
            item.get("platform"),
            item.get("source_url"),
            item.get("note"),
            item.get("match_type"),
            *item.get("tags", []),
        ]
        return keyword in " ".join(str(part or "").lower() for part in searchable_parts)
    def _insert_result(self, task_id: int, result: SearchResult) -> int:
        r = result.to_record()
        return self.db.execute("""
            INSERT INTO search_results (task_id, platform, platform_content_id, content_type, title, description, author_name, author_url, source_url, cover_url, published_at, duration_ms, public_metrics_json, matched_query, availability_status, rights_status, raw_metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, r["platform"], r["raw_metadata"].get("platform_content_id"), r["content_type"], r["title"], r["description"], r["author_name"], r["author_url"], r["source_url"], r["cover_url"], r["published_at"], r["duration_ms"], json.dumps({}, ensure_ascii=False), r["matched_query"], r["availability_status"], r["rights_status"], json.dumps(r["raw_metadata"], ensure_ascii=False))).lastrowid
