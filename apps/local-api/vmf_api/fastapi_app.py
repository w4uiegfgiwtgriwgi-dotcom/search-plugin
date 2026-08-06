from __future__ import annotations

from pydantic import Field
from .service import LocalApiService

try:
    from fastapi import FastAPI, File, HTTPException, Response, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ModuleNotFoundError:
    FastAPI = None
    File = None
    HTTPException = Exception
    Response = None
    UploadFile = object
    CORSMiddleware = None
    BaseModel = object


if FastAPI:
    app = FastAPI(title="Video Material Finder Local API", version="0.1.0-stage1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    service = LocalApiService()

    class SearchTaskRequest(BaseModel):
        query: str
        platforms: list[str] | None = None
        max_results_per_platform: int = 10

    class ProjectRequest(BaseModel):
        name: str
        note: str = ""

    class MaterialRequest(BaseModel):
        result_id: int
        tags: list[str] = Field(default_factory=list)
        note: str = ""
        selected_timestamp_ms: int | None = None

    class AnalyzeImageRequest(BaseModel):
        image_path: str

    class FindMatchRequest(BaseModel):
        query_asset_id: int
        candidate_video_path: str
        fps: float = 1.0
        threshold: float = 0.78
        refine_fps: float = 4.0
        refine_window_ms: int = 1000

    class FindBatchMatchRequest(BaseModel):
        query_asset_id: int
        candidate_video_paths: list[str]
        fps: float = 1.0
        threshold: float = 0.78
        refine_fps: float = 4.0
        refine_window_ms: int = 1000
        top_k: int = 10

    @app.get("/api/platforms")
    def list_platforms():
        return service.list_platforms()

    @app.post("/api/search/tasks", status_code=201)
    def create_search_task(request: SearchTaskRequest):
        return service.create_search_task(request.query, request.platforms, request.max_results_per_platform)

    @app.get("/api/search/tasks/{task_id}")
    def get_search_task(task_id: int):
        try:
            return service.get_search_task(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/search/tasks/{task_id}/results")
    def list_results(task_id: int):
        return service.list_results(task_id)

    @app.post("/api/projects", status_code=201)
    def create_project(request: ProjectRequest):
        return service.create_project(request.name, request.note)

    @app.get("/api/projects")
    def list_projects():
        return service.list_projects()

    @app.post("/api/projects/{project_id}/materials", status_code=201)
    def add_material(project_id: int, request: MaterialRequest):
        return service.add_material(project_id, request.result_id, request.tags, request.note, request.selected_timestamp_ms)

    @app.get("/api/projects/{project_id}/materials")
    def list_materials(project_id: int):
        return service.list_materials(project_id)

    @app.get("/api/exports/{task_id}.{fmt}")
    def export_results(task_id: int, fmt: str):
        try:
            body = service.export_results(task_id, fmt)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        media_type = {
            "json": "application/json; charset=utf-8",
            "csv": "text/csv; charset=utf-8",
            "md": "text/markdown; charset=utf-8",
        }.get(fmt, "text/plain; charset=utf-8")
        return Response(content=body, media_type=media_type)

    @app.post("/api/assets/analyze-image", status_code=201)
    def analyze_image(request: AnalyzeImageRequest):
        try:
            return service.analyze_image(request.image_path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/assets/upload-image", status_code=201)
    async def upload_image(file: UploadFile = File(...)):
        try:
            data = await file.read()
            return service.analyze_uploaded_image(file.filename or "upload.png", data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/assets/{asset_id}")
    def get_asset(asset_id: int):
        try:
            return service.get_asset(asset_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/matches/find", status_code=201)
    def find_match(request: FindMatchRequest):
        try:
            return service.find_frame_match(
                request.query_asset_id,
                request.candidate_video_path,
                request.fps,
                request.threshold,
                request.refine_fps,
                request.refine_window_ms,
            )
        except (FileNotFoundError, KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/matches/batch", status_code=201)
    def find_batch_matches(request: FindBatchMatchRequest):
        try:
            return service.find_batch_frame_matches(
                request.query_asset_id,
                request.candidate_video_paths,
                request.fps,
                request.threshold,
                request.refine_fps,
                request.refine_window_ms,
                request.top_k,
            )
        except (FileNotFoundError, KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/matches/{match_id}")
    def get_match(match_id: int):
        try:
            return service.get_match(match_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
