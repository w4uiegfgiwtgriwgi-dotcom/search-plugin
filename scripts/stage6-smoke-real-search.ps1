param(
  [string]$Query = "test video material",
  [int]$Limit = 2
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$env:PYTHONPATH = "apps/local-api"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:VMF_STAGE6_SMOKE_QUERY = $Query
$env:VMF_STAGE6_SMOKE_LIMIT = [string]$Limit

@"
import os
from vmf_api.service import LocalApiService

query = os.environ.get("VMF_STAGE6_SMOKE_QUERY", "test video material")
limit = int(os.environ.get("VMF_STAGE6_SMOKE_LIMIT", "2"))
service = LocalApiService(":memory:")
try:
    print(f"query: {query}")
    print("==> source sessions")
    platforms = {item["platform"]: item for item in service.list_platforms()}
    for platform in ["xiaohongshu", "douyin"]:
        session = platforms.get(platform, {}).get("session", {})
        login = session.get("login", {})
        print(f"{platform}: status={session.get('status')} login={login.get('status')} path={session.get('path')}")
        if session.get("hint"):
            print(f"{platform}: hint={session.get('hint')}")

    print("==> real search smoke")
    for platform in ["xiaohongshu", "douyin"]:
        task = service.create_search_task(query, [platform], limit)
        results = service.list_results(task["id"])
        print(f"{platform}: task={task['status']} results={len(results)}")
        if task.get("error_summary"):
            print(f"{platform}: error={task.get('error_summary')[:600]}")
        for item in results[:limit]:
            raw = item.get("raw_metadata_json") or {}
            print(f"{platform}: title={item.get('title')}")
            print(f"{platform}: url={item.get('source_url')}")
            print(f"{platform}: match={raw.get('semantic_match_percent')} reasons={raw.get('semantic_match_reasons')}")
finally:
    service.close()
"@ | .\.venv\Scripts\python.exe -
