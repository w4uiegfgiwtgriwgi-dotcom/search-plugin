from __future__ import annotations
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .service import LocalApiService

def _send(handler: BaseHTTPRequestHandler, status: int, body: object, content_type: str = "application/json; charset=utf-8") -> None:
    payload = body if isinstance(body, bytes) else (json.dumps(body, ensure_ascii=False).encode("utf-8") if content_type.startswith("application/json") else str(body).encode("utf-8"))
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(payload)

class ApiHandler(BaseHTTPRequestHandler):
    service = LocalApiService(os.environ.get("VMF_DB_PATH", "./.local-data/video-material-finder.sqlite"))
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.end_headers()
    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            parts = [p for p in path.split("/") if p]
            if path == "/api/platforms": return _send(self, 200, self.service.list_platforms())
            if len(parts) == 4 and parts[:3] == ["api", "search", "tasks"]: return _send(self, 200, self.service.get_search_task(int(parts[3])))
            if len(parts) == 5 and parts[:3] == ["api", "search", "tasks"] and parts[4] == "results": return _send(self, 200, self.service.list_results(int(parts[3])))
            if path == "/api/projects": return _send(self, 200, self.service.list_projects())
            if len(parts) == 5 and parts[:2] == ["api", "projects"] and parts[3] == "materials": return _send(self, 200, self.service.list_materials(int(parts[2])))
            if len(parts) == 3 and parts[:2] == ["api", "exports"]:
                task_id, fmt = parts[2].split(".", 1)
                ctype = {"json": "application/json; charset=utf-8", "csv": "text/csv; charset=utf-8", "md": "text/markdown; charset=utf-8"}.get(fmt, "text/plain; charset=utf-8")
                return _send(self, 200, self.service.export_results(int(task_id), fmt), ctype)
            return _send(self, 404, {"error": "not found"})
        except Exception as exc:
            return _send(self, 500, {"error": str(exc)})
    def do_POST(self) -> None:
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8") or "{}")
            path = urlparse(self.path).path
            parts = [p for p in path.split("/") if p]
            if path == "/api/search/tasks": return _send(self, 201, self.service.create_search_task(body.get("query", ""), body.get("platforms"), int(body.get("max_results_per_platform", 10))))
            if path == "/api/projects": return _send(self, 201, self.service.create_project(body.get("name", "未命名项目"), body.get("note", "")))
            if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "materials": return _send(self, 201, self.service.add_material(int(parts[2]), int(body["result_id"]), body.get("tags"), body.get("note", ""), body.get("selected_timestamp_ms")))
            return _send(self, 404, {"error": "not found"})
        except Exception as exc:
            return _send(self, 500, {"error": str(exc)})

def run() -> None:
    port = int(os.environ.get("LOCAL_API_PORT", "17860"))
    server = ThreadingHTTPServer(("127.0.0.1", port), ApiHandler)
    print(f"Local API listening on http://127.0.0.1:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run()
