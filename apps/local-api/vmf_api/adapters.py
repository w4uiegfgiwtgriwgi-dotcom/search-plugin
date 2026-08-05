from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
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

DEFAULT_ADAPTERS: dict[str, PlatformAdapter] = {"web-search": RecordedWebSearchAdapter(), "bilibili": MockBilibiliAdapter()}
