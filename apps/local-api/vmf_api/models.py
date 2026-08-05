from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class SearchOptions:
    platforms: list[str] = field(default_factory=lambda: ["web-search", "bilibili"])
    max_results_per_platform: int = 10
    language: str = "zh-CN"

@dataclass(frozen=True)
class SearchResult:
    platform: str
    content_type: str
    title: str
    source_url: str
    author_name: str = ""
    author_url: str = ""
    cover_url: str = ""
    published_at: str = ""
    duration_ms: int | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    matched_query: str = ""
    availability_status: str = "public"
    rights_status: str = "unknown"
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return self.__dict__.copy()
