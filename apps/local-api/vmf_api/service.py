from __future__ import annotations
import csv
import io
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
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
    MAX_BROWSER_FIELD_LENGTH = 500

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
    def _ensure_project(self, name: str) -> dict[str, Any]:
        normalized_name = str(name or "").strip() or "浏览器采集素材"
        existing = self.db.query_one("SELECT * FROM projects WHERE name = ? ORDER BY id LIMIT 1", (normalized_name,))
        if existing:
            return existing
        return self.create_project(normalized_name)
    def add_material(self, project_id: int, result_id: int, tags: list[str] | None = None, note: str = "", selected_timestamp_ms: int | None = None) -> dict[str, Any]:
        self.get_project(project_id)
        material_id = self.db.execute("""
            INSERT INTO project_materials (project_id, result_id, selected_timestamp_ms, tags_json, note)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, result_id, selected_timestamp_ms, json.dumps(tags or [], ensure_ascii=False), note)).lastrowid
        return self.get_material(material_id)
    def collect_browser_page(
        self,
        url: str,
        title: str,
        project_id: int | None = None,
        project_name: str = "浏览器采集素材",
        author_name: str = "",
        description: str = "",
        cover_url: str = "",
        published_at: str = "",
        site_name: str = "",
    ) -> dict[str, Any]:
        normalized_url = str(url or "").strip()
        normalized_title = str(title or "").strip() or "未命名页面"
        if not normalized_url.startswith(("http://", "https://")):
            raise ValueError("url 只能是 http/https 页面")
        if len(normalized_url) > 2000:
            raise ValueError("url 太长")
        normalized_title = normalized_title[: self.MAX_BROWSER_FIELD_LENGTH]
        author_name = str(author_name or "").strip()[: self.MAX_BROWSER_FIELD_LENGTH]
        description = str(description or "").strip()[: self.MAX_BROWSER_FIELD_LENGTH]
        cover_url = self._safe_browser_url(cover_url)
        published_at = str(published_at or "").strip()[: self.MAX_BROWSER_FIELD_LENGTH]
        site_name = str(site_name or "").strip()[: self.MAX_BROWSER_FIELD_LENGTH]
        project = self.get_project(project_id) if project_id else self._ensure_project(project_name)
        task_id = self.db.execute("""
            INSERT INTO search_tasks (input_type, original_query, expanded_queries_json, selected_platforms_json, filters_json, status, progress, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, 'completed', 100, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            "browser-page",
            normalized_url,
            json.dumps([normalized_title, normalized_url], ensure_ascii=False),
            json.dumps(["browser-extension"], ensure_ascii=False),
            json.dumps({"source": "browser-extension"}, ensure_ascii=False),
        )).lastrowid
        result = SearchResult(
            platform="browser-extension",
            content_type="webpage",
            title=normalized_title,
            source_url=normalized_url,
            author_name=author_name,
            cover_url=cover_url,
            published_at=published_at,
            description=description,
            matched_query=normalized_title,
            raw_metadata={
                "source": "browser-extension",
                "site_name": site_name,
                "hostname": urlparse(normalized_url).hostname or "",
            },
        )
        result_id = self._insert_result(task_id, result)
        material = self.add_material(project["id"], result_id, ["浏览器采集"], "从浏览器扩展主动采集")
        return {
            "project": project,
            "task": self.get_search_task(task_id),
            "result": self.list_results(task_id)[0],
            "material": material,
        }
    def _safe_browser_url(self, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        return normalized if normalized.startswith(("http://", "https://")) else ""
    def list_materials(self, project_id: int) -> list[dict[str, Any]]:
        rows = self.db.query_all("""
            SELECT pm.*, sr.title, sr.platform, sr.source_url, sr.cover_url, sr.author_name, sr.description, sr.published_at, sr.raw_metadata_json
            FROM project_materials pm JOIN search_results sr ON sr.id = pm.result_id
            WHERE pm.project_id = ? ORDER BY pm.id
        """, (project_id,))
        return [loads_json_fields(row, ["tags_json", "raw_metadata_json"]) for row in rows]
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
              fm.phash_score,
              fm.visual_score,
              fm.text_score,
              fm.combined_score,
              fm.local_frame_path,
              fm.evidence_json,
              ma.source_path AS query_image_path,
              ma.thumbnail_path AS query_thumbnail_path
            FROM project_frame_matches pfm
            JOIN frame_matches fm ON fm.id = pfm.match_id
            JOIN media_assets ma ON ma.id = fm.query_asset_id
            WHERE pfm.project_id = ?
            ORDER BY pfm.id DESC
        """, (project_id,))
        return [loads_json_fields(row, ["tags_json", "evidence_json"]) for row in rows]
    def get_frame_match_material(self, material_id: int) -> dict[str, Any]:
        row = self.db.query_one("""
            SELECT
              pfm.*,
              fm.query_asset_id,
              fm.candidate_video_path,
              fm.timestamp_ms,
              fm.end_timestamp_ms,
              fm.match_type,
              fm.phash_score,
              fm.visual_score,
              fm.text_score,
              fm.combined_score,
              fm.local_frame_path,
              fm.evidence_json,
              ma.source_path AS query_image_path,
              ma.thumbnail_path AS query_thumbnail_path
            FROM project_frame_matches pfm
            JOIN frame_matches fm ON fm.id = pfm.match_id
            JOIN media_assets ma ON ma.id = fm.query_asset_id
            WHERE pfm.id = ?
        """, (material_id,))
        if not row:
            raise KeyError(f"frame match material not found: {material_id}")
        return loads_json_fields(row, ["tags_json", "evidence_json"])
    def list_project_library(
        self,
        project_id: int,
        source_type: str | None = None,
        review_status: str | None = None,
        rights_status: str | None = None,
        match_confidence: str | None = None,
        keyword: str | None = None,
        sort_by: str = "created_desc",
        action_filter: str | None = None,
    ) -> dict[str, Any]:
        self.get_project(project_id)
        search_materials = [
            {
                "source_type": "search_result",
                "source_type_label": self._source_type_label("search_result"),
                "material_id": item["id"],
                "title": item["title"],
                "platform": item["platform"],
                "collection_source_label": self._collection_source_label(item),
                "source_url": item["source_url"],
                "cover_url": item["cover_url"],
                "author_name": item.get("author_name") or "",
                "description": item.get("description") or "",
                "published_at": item.get("published_at") or "",
                "site_name": (item.get("raw_metadata_json") or {}).get("site_name", ""),
                "hostname": (item.get("raw_metadata_json") or {}).get("hostname", ""),
                "selected_timestamp_ms": item["selected_timestamp_ms"],
                "selected_timecode": self._format_timecode(item["selected_timestamp_ms"]),
                "review_status": item["review_status"],
                "review_status_label": self._review_status_label(item["review_status"]),
                "rights_status": item["rights_status"],
                "rights_status_label": self._rights_status_label(item["rights_status"]),
                "tags": item["tags_json"],
                "note": item["note"],
                "created_at": item["created_at"],
            }
            for item in self.list_materials(project_id)
        ]
        frame_materials = [
            {
                "source_type": "frame_match",
                "source_type_label": self._source_type_label("frame_match"),
                "material_id": item["id"],
                "match_id": item["match_id"],
                "title": Path(item["candidate_video_path"]).name,
                "platform": "local-video",
                "source_url": item["candidate_video_path"],
                "cover_url": item["local_frame_path"],
                "selected_timestamp_ms": item["selected_timestamp_ms"],
                "selected_timecode": self._format_timecode(item["selected_timestamp_ms"]),
                "timestamp_ms": item["timestamp_ms"],
                "timecode": self._format_timecode(item["timestamp_ms"]),
                "end_timestamp_ms": item["end_timestamp_ms"],
                "end_timecode": self._format_timecode(item["end_timestamp_ms"]),
                "duration_ms": self._duration_ms(item["timestamp_ms"], item["end_timestamp_ms"]),
                "duration_timecode": self._format_timecode(self._duration_ms(item["timestamp_ms"], item["end_timestamp_ms"])),
                "match_type": item["match_type"],
                "phash_score": item["phash_score"],
                "visual_score": item["visual_score"],
                "text_score": item["text_score"],
                "combined_score": item["combined_score"],
                "match_confidence": self._match_confidence(item["combined_score"]),
                "match_confidence_label": self._match_confidence_label(item["combined_score"]),
                "evidence": item["evidence_json"],
                "evidence_summary": self._summarize_match_evidence(item["evidence_json"]),
                "review_status": item["review_status"],
                "review_status_label": self._review_status_label(item["review_status"]),
                "rights_status": item["rights_status"],
                "rights_status_label": self._rights_status_label(item["rights_status"]),
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
        for item in all_items:
            item.update(self._material_usage_status(item))
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
        if match_confidence and match_confidence != "all":
            if match_confidence not in {"high", "medium", "low"}:
                raise ValueError("match_confidence 只能是 all/high/medium/low")
            items = [item for item in items if item.get("match_confidence") == match_confidence]
        if action_filter and action_filter != "all":
            items = self._filter_library_action_items(items, action_filter)
        normalized_keyword = (keyword or "").strip().lower()
        if normalized_keyword:
            items = [item for item in items if self._library_item_matches_keyword(item, normalized_keyword)]
        if sort_by == "created_asc":
            items = sorted(items, key=lambda item: item["created_at"])
        elif sort_by == "score_desc":
            items = sorted(items, key=lambda item: item.get("combined_score") or -1, reverse=True)
        elif sort_by == "confidence_desc":
            items = sorted(items, key=lambda item: self._confidence_sort_value(item, reverse=True), reverse=True)
        elif sort_by == "confidence_asc":
            items = sorted(items, key=lambda item: self._confidence_sort_value(item, reverse=False))
        elif sort_by == "title_asc":
            items = sorted(items, key=lambda item: item["title"])
        elif sort_by == "time_asc":
            items = sorted(items, key=lambda item: self._timestamp_sort_value(item, reverse=False))
        elif sort_by == "time_desc":
            items = sorted(items, key=lambda item: self._timestamp_sort_value(item, reverse=True), reverse=True)
        elif sort_by == "created_desc":
            items = sorted(items, key=lambda item: item["created_at"], reverse=True)
        else:
            raise ValueError("sort_by 只能是 created_desc/created_asc/score_desc/confidence_desc/confidence_asc/title_asc/time_asc/time_desc")
        return {
            "project_id": project_id,
            "total_count": len(items),
            "search_result_count": sum(1 for item in items if item["source_type"] == "search_result"),
            "frame_match_count": sum(1 for item in items if item["source_type"] == "frame_match"),
            "filters": self._build_library_filters(source_type, review_status, rights_status, match_confidence, keyword, sort_by, action_filter),
            "filter_summary": self._library_filter_summary(source_type, review_status, rights_status, match_confidence, keyword, sort_by, action_filter),
            "summary": self._build_library_summary(all_items, items),
            "timeline": self._build_frame_match_timeline(items),
            "action_items": self._build_library_action_items(items),
            "items": items,
        }
    def export_project_library(
        self,
        project_id: int,
        fmt: str,
        source_type: str | None = None,
        review_status: str | None = None,
        rights_status: str | None = None,
        match_confidence: str | None = None,
        keyword: str | None = None,
        sort_by: str = "created_desc",
        action_filter: str | None = None,
    ) -> str:
        library = self.list_project_library(project_id, source_type, review_status, rights_status, match_confidence, keyword, sort_by, action_filter)
        items = library["items"]
        if fmt == "json":
            return json.dumps(library, ensure_ascii=False, indent=2)
        if fmt == "csv":
            output = io.StringIO()
            fields = [
                "source_type",
                "source_type_label",
                "material_id",
                "title",
                "platform",
                "source_url",
                "selected_timestamp_ms",
                "selected_timecode",
                "timecode",
                "end_timecode",
                "duration_ms",
                "duration_timecode",
                "combined_score",
                "phash_score",
                "visual_score",
                "text_score",
                "match_confidence",
                "match_confidence_label",
                "usage_status",
                "usage_status_label",
                "usage_status_reason",
                "evidence_summary",
                "review_status",
                "review_status_label",
                "rights_status",
                "rights_status_label",
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
            lines = [
                f"# 项目 {project_id} 素材库",
                "",
                "## 导出概览",
                "",
                f"- 导出条件：{library['filter_summary']}",
                f"- 当前导出：{library['total_count']} 条",
                f"- 项目全部：{library['summary']['all_count']} 条",
                f"- 搜索收藏：{library['search_result_count']} 条",
                f"- 截图反查：{library['frame_match_count']} 条",
                "",
            ]
            timeline_lines = self._build_frame_match_timeline_lines(items)
            action_lines = self._build_library_action_lines(items)
            if action_lines:
                lines.extend(["## 待处理清单", "", *action_lines, ""])
            if timeline_lines:
                lines.extend(["## 截图反查时间线", "", *timeline_lines, ""])
            lines.extend(["## 素材列表", ""])
            for item in items:
                tags = " / ".join(item.get("tags") or []) or "未打标签"
                lines.append(f"- **{item['title']}** ({item.get('source_type_label') or item['source_type']})")
                lines.append(f"  - 来源：{item['source_url']}")
                review_label = item.get("review_status_label") or item["review_status"]
                rights_label = item.get("rights_status_label") or item["rights_status"]
                lines.append(f"  - 状态：{review_label}，版权：{rights_label}，标签：{tags}")
                if item.get("usage_status_label"):
                    lines.append(f"  - 可用状态：{item['usage_status_label']}，原因：{item.get('usage_status_reason') or '待确认'}")
                if item.get("selected_timestamp_ms") is not None:
                    lines.append(f"  - 时间点：{item['selected_timestamp_ms']}ms")
                if item.get("timecode"):
                    lines.append(f"  - 时间码：{item['timecode']}")
                if item.get("duration_timecode"):
                    lines.append(f"  - 时长：{item['duration_timecode']}")
                if item.get("combined_score") is not None:
                    lines.append(f"  - 匹配分：{item['combined_score']}")
                if item.get("match_confidence_label"):
                    lines.append(f"  - 可信度：{item['match_confidence_label']}")
                if item.get("evidence_summary"):
                    lines.append(f"  - 证据：{item['evidence_summary']}")
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
            "by_match_confidence": {
                status: self._count_library_items(all_items, "match_confidence", status)
                for status in ["high", "medium", "low"]
            },
            "by_usage_status": {
                status: self._count_library_items(all_items, "usage_status", status)
                for status in ["ready", "needs_review", "rights_unknown", "needs_permission", "low_confidence", "unavailable"]
            },
        }
    def _count_library_items(self, items: list[dict[str, Any]], key: str, value: str) -> int:
        return sum(1 for item in items if item.get(key) == value)
    def _material_usage_status(self, item: dict[str, Any]) -> dict[str, str]:
        review_status = item.get("review_status")
        rights_status = item.get("rights_status")
        match_confidence = item.get("match_confidence")
        if review_status == "rejected" or rights_status == "blocked":
            return {
                "usage_status": "unavailable",
                "usage_status_label": "不可用",
                "usage_status_reason": "素材已被拒绝或版权标记为不可用",
            }
        if rights_status == "needs_permission":
            return {
                "usage_status": "needs_permission",
                "usage_status_label": "需授权",
                "usage_status_reason": "使用前需要先确认授权",
            }
        if review_status == "pending":
            return {
                "usage_status": "needs_review",
                "usage_status_label": "待复核",
                "usage_status_reason": "还没有人工确认素材是否匹配需求",
            }
        if match_confidence == "low":
            return {
                "usage_status": "low_confidence",
                "usage_status_label": "低可信待确认",
                "usage_status_reason": "截图反查匹配分较低，建议先回看时间点",
            }
        if rights_status == "unknown":
            return {
                "usage_status": "rights_unknown",
                "usage_status_label": "版权待确认",
                "usage_status_reason": "版权状态未知，暂不建议直接用于交付",
            }
        if review_status == "confirmed" and rights_status == "cleared":
            return {
                "usage_status": "ready",
                "usage_status_label": "可用",
                "usage_status_reason": "已确认且版权标记为可用",
            }
        return {
            "usage_status": "needs_review",
            "usage_status_label": "待复核",
            "usage_status_reason": "素材状态还需要人工确认",
        }
    def _filter_library_action_items(self, items: list[dict[str, Any]], action_filter: str) -> list[dict[str, Any]]:
        if action_filter == "pending_review":
            return [item for item in items if item.get("review_status") == "pending"]
        if action_filter == "rights_attention":
            return [item for item in items if item.get("rights_status") in {"needs_permission", "blocked"}]
        if action_filter == "low_confidence":
            return [item for item in items if item.get("match_confidence") == "low"]
        raise ValueError("action_filter 只能是 all/pending_review/rights_attention/low_confidence")
    def _build_library_action_items(self, items: list[dict[str, Any]], limit: int = 5) -> dict[str, Any]:
        groups = {
            "pending_review": [item for item in items if item.get("review_status") == "pending"],
            "rights_attention": [item for item in items if item.get("rights_status") in {"needs_permission", "blocked"}],
            "low_confidence": [item for item in items if item.get("match_confidence") == "low"],
        }
        return {
            "counts": {name: len(group) for name, group in groups.items()},
            "filters": {
                "pending_review": {"action_filter": "pending_review", "review_status": "pending"},
                "rights_attention": {"action_filter": "rights_attention", "rights_status": "needs_permission/blocked"},
                "low_confidence": {"action_filter": "low_confidence", "match_confidence": "low"},
            },
            **{name: [self._action_item_brief(item, name) for item in group[:limit]] for name, group in groups.items()},
        }
    def _action_item_brief(self, item: dict[str, Any], action_type: str) -> dict[str, Any]:
        guidance = self._action_item_guidance(item, action_type)
        return {
            "action_type": action_type,
            **guidance,
            "source_type": item.get("source_type"),
            "source_type_label": item.get("source_type_label"),
            "material_id": item.get("material_id"),
            "title": item.get("title"),
            "source_url": item.get("source_url"),
            "review_status": item.get("review_status"),
            "review_status_label": item.get("review_status_label"),
            "rights_status": item.get("rights_status"),
            "rights_status_label": item.get("rights_status_label"),
            "match_confidence": item.get("match_confidence"),
            "match_confidence_label": item.get("match_confidence_label"),
            "timecode": item.get("timecode") or item.get("selected_timecode"),
            "duration_timecode": item.get("duration_timecode"),
            "combined_score": item.get("combined_score"),
        }
    def _action_item_guidance(self, item: dict[str, Any], action_type: str) -> dict[str, str]:
        if action_type == "pending_review":
            return {
                "action_label": "待复核",
                "priority": "medium",
                "action_reason": "素材还没有人工确认",
                "suggested_next_step": "打开来源核对标题、画面和备注，再标为已确认或已拒绝",
            }
        if action_type == "rights_attention":
            if item.get("rights_status") == "blocked":
                return {
                    "action_label": "版权不可用",
                    "priority": "high",
                    "action_reason": "素材已标记为不可用",
                    "suggested_next_step": "替换素材或保留为参考，不要放入可交付清单",
                }
            return {
                "action_label": "版权需处理",
                "priority": "high",
                "action_reason": "素材需要先确认授权",
                "suggested_next_step": "确认授权来源，能使用就标为可用，否则标为不可用",
            }
        if action_type == "low_confidence":
            return {
                "action_label": "低可信",
                "priority": "medium",
                "action_reason": "截图反查匹配可信度较低",
                "suggested_next_step": "回看时间点和证据摘要，必要时重新匹配或换候选视频",
            }
        return {
            "action_label": action_type,
            "priority": "low",
            "action_reason": "需要人工确认",
            "suggested_next_step": "查看素材详情后决定是否保留",
        }
    def _build_library_action_lines(self, items: list[dict[str, Any]]) -> list[str]:
        action_items = self._build_library_action_items(items)
        labels = {
            "pending_review": "待复核",
            "rights_attention": "版权需处理",
            "low_confidence": "低可信",
        }
        lines: list[str] = []
        for group_name, label in labels.items():
            count = action_items["counts"][group_name]
            if count == 0:
                continue
            lines.append(f"- {label}：{count} 条")
            for item in action_items[group_name]:
                timecode = f" @ {item['timecode']}" if item.get("timecode") else ""
                confidence = f"，{item['match_confidence_label']}" if item.get("match_confidence_label") else ""
                rights = f"，版权：{item['rights_status_label']}" if item.get("rights_status_label") else ""
                suggestion = f"，建议：{item['suggested_next_step']}" if item.get("suggested_next_step") else ""
                lines.append(f"  - {item['title']}{timecode}{confidence}{rights}{suggestion}")
        return lines
    def _build_frame_match_timeline(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        frame_items = [item for item in items if item.get("source_type") == "frame_match"]
        frame_items.sort(key=lambda item: self._timestamp_sort_value(item, reverse=False))
        timeline: list[dict[str, Any]] = []
        for item in frame_items:
            timeline.append({
                "material_id": item["material_id"],
                "match_id": item.get("match_id"),
                "title": item["title"],
                "source_url": item["source_url"],
                "timestamp_ms": item.get("timestamp_ms"),
                "timecode": item.get("timecode") or item.get("selected_timecode"),
                "end_timestamp_ms": item.get("end_timestamp_ms"),
                "end_timecode": item.get("end_timecode"),
                "duration_ms": item.get("duration_ms"),
                "duration_timecode": item.get("duration_timecode"),
                "combined_score": item.get("combined_score"),
                "match_confidence": item.get("match_confidence"),
                "match_confidence_label": item.get("match_confidence_label"),
            })
        return timeline
    def _build_frame_match_timeline_lines(self, items: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for item in self._build_frame_match_timeline(items):
            timecode = item.get("timecode") or "未知时间"
            duration = item.get("duration_timecode") or "未知时长"
            confidence = item.get("match_confidence_label") or "未知可信度"
            score = item.get("combined_score")
            score_text = f"，匹配分 {score}" if score is not None else ""
            lines.append(f"- {timecode} · {duration} · {confidence}{score_text} · {item['title']}")
        return lines
    def _build_library_filters(
        self,
        source_type: str | None,
        review_status: str | None,
        rights_status: str | None,
        match_confidence: str | None,
        keyword: str | None,
        sort_by: str,
        action_filter: str | None,
    ) -> dict[str, str]:
        return {
            "source_type": source_type or "all",
            "review_status": review_status or "all",
            "rights_status": rights_status or "all",
            "match_confidence": match_confidence or "all",
            "action_filter": action_filter or "all",
            "keyword": (keyword or "").strip(),
            "sort_by": sort_by,
        }
    def _library_filter_summary(
        self,
        source_type: str | None,
        review_status: str | None,
        rights_status: str | None,
        match_confidence: str | None,
        keyword: str | None,
        sort_by: str,
        action_filter: str | None,
    ) -> str:
        filters = self._build_library_filters(source_type, review_status, rights_status, match_confidence, keyword, sort_by, action_filter)
        parts = [
            f"来源={self._filter_value_label('source_type', filters['source_type'])}",
            f"复核={self._filter_value_label('review_status', filters['review_status'])}",
            f"版权={self._filter_value_label('rights_status', filters['rights_status'])}",
            f"可信度={self._filter_value_label('match_confidence', filters['match_confidence'])}",
            f"待处理={self._filter_value_label('action_filter', filters['action_filter'])}",
            f"排序={self._filter_value_label('sort_by', filters['sort_by'])}",
        ]
        if filters["keyword"]:
            parts.append(f"关键词={filters['keyword']}")
        return "，".join(parts)
    def _filter_value_label(self, field: str, value: str) -> str:
        if value == "all":
            return "全部"
        if field == "source_type":
            return self._source_type_label(value)
        if field == "review_status":
            return self._review_status_label(value)
        if field == "rights_status":
            return self._rights_status_label(value)
        if field == "match_confidence":
            return {"high": "高可信", "medium": "中可信", "low": "低可信"}.get(value, value)
        if field == "action_filter":
            return {
                "pending_review": "待复核",
                "rights_attention": "版权需处理",
                "low_confidence": "低可信",
            }.get(value, value)
        if field == "sort_by":
            return {
                "created_desc": "最新在前",
                "created_asc": "最早在前",
                "score_desc": "匹配分高在前",
                "confidence_desc": "可信度高在前",
                "confidence_asc": "可信度低在前",
                "title_asc": "标题 A-Z",
                "time_asc": "时间点早在前",
                "time_desc": "时间点晚在前",
            }.get(value, value)
        return value
    def _confidence_sort_value(self, item: dict[str, Any], reverse: bool) -> int:
        order = {"low": 1, "medium": 2, "high": 3}
        value = order.get(item.get("match_confidence"), 0)
        if value == 0:
            return -1 if reverse else 99
        return value
    def _library_item_matches_keyword(self, item: dict[str, Any], keyword: str) -> bool:
        searchable_parts = [
            item.get("title"),
            item.get("platform"),
            item.get("source_url"),
            item.get("source_type_label"),
            item.get("review_status_label"),
            item.get("rights_status_label"),
            item.get("usage_status_label"),
            item.get("usage_status_reason"),
            item.get("note"),
            item.get("match_type"),
            item.get("timecode"),
            item.get("selected_timecode"),
            item.get("duration_timecode"),
            item.get("match_confidence"),
            item.get("match_confidence_label"),
            item.get("evidence_summary"),
            *item.get("tags", []),
        ]
        return keyword in " ".join(str(part or "").lower() for part in searchable_parts)
    def _source_type_label(self, source_type: str) -> str:
        return {
            "search_result": "搜索收藏",
            "frame_match": "截图反查",
        }.get(source_type, source_type)
    def _collection_source_label(self, item: dict[str, Any]) -> str:
        if item.get("platform") == "browser-extension":
            return "浏览器采集"
        return self._source_type_label("search_result")
    def _review_status_label(self, review_status: str) -> str:
        return {
            "pending": "待复核",
            "confirmed": "已确认",
            "rejected": "已拒绝",
        }.get(review_status, review_status)
    def _rights_status_label(self, rights_status: str) -> str:
        return {
            "unknown": "未知",
            "cleared": "可用",
            "needs_permission": "需授权",
            "blocked": "不可用",
        }.get(rights_status, rights_status)
    def _match_confidence(self, combined_score: float | None) -> str | None:
        if combined_score is None:
            return None
        score = float(combined_score)
        if score >= 0.85:
            return "high"
        if score >= 0.7:
            return "medium"
        return "low"
    def _match_confidence_label(self, combined_score: float | None) -> str | None:
        confidence = self._match_confidence(combined_score)
        return {
            "high": "高可信",
            "medium": "中可信",
            "low": "低可信",
        }.get(confidence)
    def _summarize_match_evidence(self, evidence: dict[str, Any] | None) -> str:
        if not evidence:
            return ""
        parts: list[str] = []
        if evidence.get("frame_count") is not None:
            parts.append(f"粗扫{evidence['frame_count']}帧")
        if evidence.get("refined_frame_count") is not None:
            parts.append(f"精排{evidence['refined_frame_count']}帧")
        if evidence.get("fps") is not None:
            parts.append(f"粗扫FPS {evidence['fps']}")
        if evidence.get("refine_fps") is not None:
            parts.append(f"精排FPS {evidence['refine_fps']}")
        if evidence.get("threshold") is not None:
            parts.append(f"阈值 {evidence['threshold']}")
        if evidence.get("coarse_best_timestamp_ms") is not None:
            parts.append(f"粗扫最佳 {self._format_timecode(evidence['coarse_best_timestamp_ms'])}")
        return "，".join(parts)
    def _format_timecode(self, timestamp_ms: int | None) -> str | None:
        if timestamp_ms is None:
            return None
        total_ms = max(0, int(timestamp_ms))
        milliseconds = total_ms % 1000
        total_seconds = total_ms // 1000
        seconds = total_seconds % 60
        total_minutes = total_seconds // 60
        minutes = total_minutes % 60
        hours = total_minutes // 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    def _duration_ms(self, start_ms: int | None, end_ms: int | None) -> int | None:
        if start_ms is None or end_ms is None:
            return None
        return max(0, int(end_ms) - int(start_ms))
    def _timestamp_sort_value(self, item: dict[str, Any], reverse: bool) -> int:
        timestamp = item.get("selected_timestamp_ms")
        if timestamp is None:
            return -1 if reverse else 2**63 - 1
        return int(timestamp)
    def _insert_result(self, task_id: int, result: SearchResult) -> int:
        r = result.to_record()
        return self.db.execute("""
            INSERT INTO search_results (task_id, platform, platform_content_id, content_type, title, description, author_name, author_url, source_url, cover_url, published_at, duration_ms, public_metrics_json, matched_query, availability_status, rights_status, raw_metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, r["platform"], r["raw_metadata"].get("platform_content_id"), r["content_type"], r["title"], r["description"], r["author_name"], r["author_url"], r["source_url"], r["cover_url"], r["published_at"], r["duration_ms"], json.dumps({}, ensure_ascii=False), r["matched_query"], r["availability_status"], r["rights_status"], json.dumps(r["raw_metadata"], ensure_ascii=False))).lastrowid
