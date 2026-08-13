from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
import re
import shlex
import shutil
import subprocess
from typing import Any
from .models import SearchOptions, SearchResult
from .query import normalize_url

@dataclass(frozen=True)
class PlatformCapabilities:
    supports_public_search: bool
    supports_login_session: bool
    supports_pagination: bool
    supports_video_download: bool
    notes: str

class PlatformAdapter(ABC):
    platform: str
    @abstractmethod
    def capabilities(self) -> PlatformCapabilities: ...
    def check_session(self) -> dict[str, Any]:
        return {"platform": self.platform, "status": "not_required"}
    @abstractmethod
    def search(self, query: str, options: SearchOptions) -> list[SearchResult]: ...

class RecordedWebSearchAdapter(PlatformAdapter):
    platform = "web-search"
    def capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(True, False, False, False, "Stage 1 uses recorded public-web sample results.")
    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        return [
            SearchResult(self.platform, "web_page", "极端高温废墟里发现旧空调", normalize_url("https://example.com/video/heat-dump-air-conditioner?utm_source=fixture"), author_name="Public Demo Archive", cover_url="https://example.com/covers/heat.jpg", published_at="2026-07-01", description="公开视频搜索录制样本，用于验证字段归一化。", tags=["高温", "废墟", "空调"], matched_query=query, raw_metadata={"fixture": "web-search"}),
            SearchResult(self.platform, "article", "公开视频素材检索方法", "https://example.com/article/video-material-search", author_name="Open Web Notes", cover_url="https://example.com/covers/search.jpg", published_at="2026-06-18", description="公开网页素材检索说明样本。", tags=["素材", "检索"], matched_query=query, raw_metadata={"fixture": "web-search"}),
        ][: options.max_results_per_platform]

class MockBilibiliAdapter(PlatformAdapter):
    platform = "bilibili"
    def capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(True, False, True, False, "Stage 1 mock adapter; no login or scraping.")
    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        return [SearchResult(self.platform, "video", "B站公开结果样本：废墟里的旧空调", "https://www.bilibili.com/video/BV1stage1001", author_name="公开样本账号", author_url="https://space.bilibili.com/1001", cover_url="https://example.com/bilibili/cover-1001.jpg", published_at="2026-06-30", duration_ms=92000, description="用于阶段1验证的平台适配器样本，不访问真实账号。", tags=["B站", "公开视频", "空调"], matched_query=query, raw_metadata={"fixture": "bilibili", "platform_content_id": "BV1stage1001"})][: options.max_results_per_platform]

class SemanticMatchScorer:
    def score(self, query: str, result: SearchResult) -> dict[str, Any]:
        query_terms = self._terms(query)
        title = result.title or ""
        description = result.description or ""
        tags = " ".join(result.tags or [])
        haystack = " ".join([title, description, tags, result.author_name or ""])
        haystack_terms = self._terms(haystack)
        query_chars = self._cjk_chars(query)
        haystack_chars = self._cjk_chars(haystack)

        score = 0.12
        reasons: list[str] = []
        title_hits = [term for term in query_terms if term and term in title.lower()]
        desc_hits = [term for term in query_terms if term and term in description.lower()]
        tag_hits = [term for term in query_terms if term and term in tags.lower()]
        overlap = len(query_terms & haystack_terms) / max(len(query_terms), 1)
        char_overlap = len(query_chars & haystack_chars) / max(len(query_chars), 1)

        if title_hits:
            score += min(0.34, 0.12 + len(title_hits) * 0.055)
            reasons.append(f"标题命中：{'、'.join(title_hits[:4])}")
        if desc_hits:
            score += min(0.24, 0.08 + len(desc_hits) * 0.04)
            reasons.append(f"描述命中：{'、'.join(desc_hits[:4])}")
        if tag_hits:
            score += min(0.12, 0.04 + len(tag_hits) * 0.03)
            reasons.append(f"标签命中：{'、'.join(tag_hits[:4])}")
        if overlap > 0:
            score += min(0.18, overlap * 0.18)
            reasons.append(f"关键词重合度约 {round(overlap * 100)}%")
        if char_overlap > 0:
            score += min(0.12, char_overlap * 0.12)
        if result.cover_url:
            score += 0.03
            reasons.append("结果带封面，可供后续视觉复核")
        if result.duration_ms:
            score += 0.02

        score = round(min(score, 0.96), 4)
        if not reasons:
            reasons.append("仅命中平台返回的弱相关候选，建议人工打开复核画面")
        return {
            "semantic_match_score": score,
            "semantic_match_percent": round(score * 100),
            "semantic_match_reasons": reasons,
            "semantic_match_basis": "title+description+tags+public_metadata",
            "semantic_match_warning": "当前阶段只基于公开视频公开元数据评分；没有字幕、关键帧或真实视觉模型时，不能等同于已确认画面内容。",
        }

    def _terms(self, value: str) -> set[str]:
        normalized = str(value or "").lower()
        words = set(re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", normalized))
        compact = re.sub(r"\s+", "", normalized)
        cjk = "".join(self._cjk_chars(compact))
        bigrams = {cjk[index:index + 2] for index in range(max(len(cjk) - 1, 0))}
        trigrams = {cjk[index:index + 3] for index in range(max(len(cjk) - 2, 0))}
        return {item for item in words | bigrams | trigrams if item}

    def _cjk_chars(self, value: str) -> set[str]:
        return set(re.findall(r"[\u4e00-\u9fff]", str(value or "")))

class ExternalCliSearchAdapter(PlatformAdapter):
    platform = ""
    command_template_env = ""
    default_command_template = ""
    platform_label = ""

    def __init__(self):
        self.scorer = SemanticMatchScorer()

    def capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            True,
            False,
            True,
            False,
            f"阶段6真实候选源桥接：只调用本机 {self.platform_label} 搜索 CLI 的公开搜索/详情输出，不接下载、点赞、评论、发布或绕登录。",
        )

    def check_session(self) -> dict[str, Any]:
        command = self._command_template().split()[0]
        executable = shutil.which(command)
        return {
            "platform": self.platform,
            "status": "available" if executable else "not_configured",
            "command": command,
            "hint": "" if executable else f"未找到 {command} 命令；安装对应开源 CLI 后，或设置 {self.command_template_env} 指向实际搜索命令。",
        }

    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        command = self._build_command(query, options.max_results_per_platform)
        executable = shutil.which(command[0])
        if not executable:
            raise RuntimeError(f"未配置 {self.platform_label} 搜索 CLI：找不到 {command[0]}。请先安装对应开源工具，或设置 {self.command_template_env}。")
        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=45,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"{self.platform_label} 搜索 CLI 执行失败：{detail[:500]}")
        payload = self._load_json(completed.stdout)
        results = [self._result_from_item(item, query) for item in self._extract_items(payload)]
        return results[: options.max_results_per_platform]

    def _command_template(self) -> str:
        return os.environ.get(self.command_template_env, self.default_command_template)

    def _build_command(self, query: str, limit: int) -> list[str]:
        template = self._command_template().format(query=query, limit=max(1, int(limit)))
        return shlex.split(template)

    def _load_json(self, output: str) -> Any:
        text = str(output or "").strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", text, re.S)
            if not match:
                raise RuntimeError("CLI 没有输出可解析 JSON")
            return json.loads(match.group(1))

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("items", "data", "results", "notes", "aweme_list", "videos"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
                if isinstance(value, dict):
                    nested = self._extract_items(value)
                    if nested:
                        return nested
        return []

    def _pick(self, item: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return ""

    def _first_url(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            for entry in value:
                url = self._first_url(entry)
                if url:
                    return url
        if isinstance(value, dict):
            for key in ("url", "href", "link"):
                url = self._first_url(value.get(key))
                if url:
                    return url
        return ""

    def _result_from_item(self, item: dict[str, Any], query: str) -> SearchResult:
        title = str(self._pick(item, "title", "desc", "description", "note_display_title", "caption", "content") or "未命名视频")
        description = str(self._pick(item, "description", "desc", "caption", "content", "summary") or "")
        source_url = self._source_url(item)
        cover_url = self._first_url(self._pick(item, "cover_url", "cover", "image", "images", "thumbnail", "video_cover"))
        author = self._pick(item, "author_name", "author", "nickname", "user_name", "user", "creator")
        if isinstance(author, dict):
            author = self._pick(author, "nickname", "name", "user_name")
        tags = self._tags(item)
        result = SearchResult(
            self.platform,
            "video",
            title,
            source_url,
            author_name=str(author or ""),
            cover_url=cover_url,
            published_at=str(self._pick(item, "published_at", "publish_time", "created_at", "time", "date") or ""),
            description=description,
            tags=tags,
            matched_query=query,
            raw_metadata={
                "provider": self.__class__.__name__,
                "raw": item,
                "source": "external-cli",
            },
        )
        result.raw_metadata.update(self.scorer.score(query, result))
        return result

    def _source_url(self, item: dict[str, Any]) -> str:
        return normalize_url(str(self._pick(item, "source_url", "url", "share_url", "link", "href", "note_url", "aweme_url") or ""))

    def _tags(self, item: dict[str, Any]) -> list[str]:
        value = self._pick(item, "tags", "tag_list", "hashtags", "keywords")
        if isinstance(value, str):
            return [part.strip("# ") for part in re.split(r"[,，\s]+", value) if part.strip("# ")]
        if isinstance(value, list):
            tags: list[str] = []
            for entry in value:
                if isinstance(entry, str):
                    tags.append(entry.strip("# "))
                elif isinstance(entry, dict):
                    tag = self._pick(entry, "name", "tag_name", "title")
                    if tag:
                        tags.append(str(tag).strip("# "))
            return [tag for tag in tags if tag]
        return []

class XiaohongshuCliAdapter(ExternalCliSearchAdapter):
    platform = "xiaohongshu"
    platform_label = "小红书"
    command_template_env = "VMF_XHS_SEARCH_COMMAND"
    default_command_template = 'xhs search "{query}" --json --limit {limit}'

class DouyinCliAdapter(ExternalCliSearchAdapter):
    platform = "douyin"
    platform_label = "抖音"
    command_template_env = "VMF_DOUYIN_SEARCH_COMMAND"
    default_command_template = 'dy search "{query}" --json --limit {limit}'

    def _source_url(self, item: dict[str, Any]) -> str:
        source = self._pick(item, "source_url", "url", "share_url", "link", "href", "aweme_url")
        if source:
            return normalize_url(str(source))
        aweme_id = self._pick(item, "aweme_id", "id", "video_id")
        return f"https://www.douyin.com/video/{aweme_id}" if aweme_id else ""

DEFAULT_ADAPTERS: dict[str, PlatformAdapter] = {
    "web-search": RecordedWebSearchAdapter(),
    "bilibili": MockBilibiliAdapter(),
    "xiaohongshu": XiaohongshuCliAdapter(),
    "douyin": DouyinCliAdapter(),
}
