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

    class FrameMatchMaterialRequest(BaseModel):
        match_id: int
        tags: list[str] = Field(default_factory=list)
        note: str = ""
        review_status: str = "confirmed"

    class BatchFrameMatchMaterialRequest(BaseModel):
        match_ids: list[int]
        min_score: float = 0.75
        tags: list[str] = Field(default_factory=list)
        note: str = ""
        review_status: str = "confirmed"

    class ReviewStatusRequest(BaseModel):
        review_status: str

    class RightsStatusRequest(BaseModel):
        rights_status: str

    class MaterialMetadataRequest(BaseModel):
        tags: list[str] = Field(default_factory=list)
        note: str = ""

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

    class FindMultiAssetMatchRequest(BaseModel):
        query_asset_ids: list[int]
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

    @app.get("/api/projects/{project_id}/library")
    def list_project_library(
        project_id: int,
        source_type: str = "all",
        review_status: str = "all",
        rights_status: str = "all",
        sort_by: str = "created_desc",
    ):
        try:
            return service.list_project_library(project_id, source_type, review_status, rights_status, sort_by)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/library.{fmt}")
    def export_project_library(
        project_id: int,
        fmt: str,
        source_type: str = "all",
        review_status: str = "all",
        rights_status: str = "all",
        sort_by: str = "created_desc",
    ):
        try:
            body = service.export_project_library(project_id, fmt, source_type, review_status, rights_status, sort_by)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        media_type = {
            "json": "application/json; charset=utf-8",
            "csv": "text/csv; charset=utf-8",
            "md": "text/markdown; charset=utf-8",
        }.get(fmt, "text/plain; charset=utf-8")
        return Response(content=body, media_type=media_type)

    @app.post("/api/projects/{project_id}/library/{source_type}/{material_id}/review-status")
    def update_material_review_status(project_id: int, source_type: str, material_id: int, request: ReviewStatusRequest):
        try:
            return service.update_material_review_status(project_id, source_type, material_id, request.review_status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/library/{source_type}/{material_id}/rights-status")
    def update_material_rights_status(project_id: int, source_type: str, material_id: int, request: RightsStatusRequest):
        try:
            return service.update_material_rights_status(project_id, source_type, material_id, request.rights_status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/library/{source_type}/{material_id}/metadata")
    def update_material_metadata(project_id: int, source_type: str, material_id: int, request: MaterialMetadataRequest):
        try:
            return service.update_material_metadata(project_id, source_type, material_id, request.tags, request.note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/frame-matches", status_code=201)
    def add_frame_match_material(project_id: int, request: FrameMatchMaterialRequest):
        try:
            return service.add_frame_match_material(project_id, request.match_id, request.tags, request.note, request.review_status)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/frame-matches/batch", status_code=201)
    def add_frame_match_materials(project_id: int, request: BatchFrameMatchMaterialRequest):
        try:
            return service.add_frame_match_materials(
                project_id,
                request.match_ids,
                request.min_score,
                request.tags,
                request.note,
                request.review_status,
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/frame-matches")
    def list_frame_match_materials(project_id: int):
        try:
            return service.list_frame_match_materials(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

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

    @app.post("/api/assets/upload-images", status_code=201)
    async def upload_images(files: list[UploadFile] = File(...)):
        try:
            uploads = [(file.filename or "upload.png", await file.read()) for file in files]
            return service.analyze_uploaded_images(uploads)
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

    @app.post("/api/matches/batch-assets", status_code=201)
    def find_multi_asset_matches(request: FindMultiAssetMatchRequest):
        try:
            return service.find_multi_asset_frame_matches(
                request.query_asset_ids,
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
