from __future__ import annotations
from .service import LocalApiService
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ModuleNotFoundError:
    FastAPI = None
    HTTPException = Exception
    BaseModel = object

if FastAPI:
    app = FastAPI(title="Video Material Finder Local API", version="0.1.0-stage1")
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
        tags: list[str] = []
        note: str = ""
        selected_timestamp_ms: int | None = None
    @app.get("/api/platforms")
    def list_platforms(): return service.list_platforms()
    @app.post("/api/search/tasks", status_code=201)
    def create_search_task(request: SearchTaskRequest): return service.create_search_task(request.query, request.platforms, request.max_results_per_platform)
    @app.get("/api/search/tasks/{task_id}")
    def get_search_task(task_id: int):
        try: return service.get_search_task(task_id)
        except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    @app.get("/api/search/tasks/{task_id}/results")
    def list_results(task_id: int): return service.list_results(task_id)
    @app.post("/api/projects", status_code=201)
    def create_project(request: ProjectRequest): return service.create_project(request.name, request.note)
    @app.get("/api/projects")
    def list_projects(): return service.list_projects()
    @app.post("/api/projects/{project_id}/materials", status_code=201)
    def add_material(project_id: int, request: MaterialRequest): return service.add_material(project_id, request.result_id, request.tags, request.note, request.selected_timestamp_ms)
    @app.get("/api/projects/{project_id}/materials")
    def list_materials(project_id: int): return service.list_materials(project_id)
