from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = os.environ.get("VMF_API_BASE", "http://127.0.0.1:17860").rstrip("/")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    data = None
    headers = {"content-type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    payload = {
        "url": "https://example.com/stage3-browser-smoke",
        "title": "阶段3浏览器采集冒烟页面",
        "project_name": "阶段3浏览器采集验收",
        "author_name": "Smoke Test",
        "description": "模拟浏览器扩展主动采集的公开页面",
        "cover_url": "https://example.com/cover.jpg",
        "published_at": "2026-08-10T12:00:00+08:00",
        "site_name": "Example",
    }
    try:
        collected = request_json("/api/browser/collect-page", "POST", payload)
        project_id = collected["project"]["id"]
        query = urlencode({"keyword": "阶段3浏览器采集冒烟页面"})
        library = request_json(f"/api/projects/{project_id}/library?{query}")
    except (HTTPError, URLError, TimeoutError) as exc:
        print(json.dumps({
            "passed": False,
            "error": str(exc),
            "hint": "请先启动桌面端或本地 API，确认 127.0.0.1:17860 可访问",
        }, ensure_ascii=False, indent=2))
        return 1

    item = library["items"][0] if library.get("items") else {}
    passed = (
        collected["result"]["platform"] == "browser-extension"
        and item.get("collection_source_label") == "浏览器采集"
        and item.get("site_name") == "Example"
    )
    print(json.dumps({
        "passed": passed,
        "project_id": project_id,
        "material_id": collected["material"]["id"],
        "title": item.get("title"),
        "source": item.get("collection_source_label"),
        "site_name": item.get("site_name"),
    }, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
