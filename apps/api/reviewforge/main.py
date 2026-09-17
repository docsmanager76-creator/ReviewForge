from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import load_config, ensure_data_dirs
from .db.database import get_connection, init_schema
from .db.repository import ProjectRepository
from .models.file_reference import resolve_local_path
from .models.schemas import (
    CreateProjectRequest,
    HealthResponse,
    ProjectDetail,
    ProjectDirectories,
    ProjectSummary,
    ProductInput,
)
from .util.filesystem import create_project_directories, project_directory_map

config = load_config()
ensure_data_dirs(config)

app = FastAPI(title="ReviewForge API", version=__version__)

# Local-first: the UI only ever runs on localhost, so CORS is locked to that origin set.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_repository() -> ProjectRepository:
    conn = get_connection(config.db_path)
    init_schema(conn)
    return ProjectRepository(conn)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.get("/projects", response_model=list[ProjectSummary])
def list_projects() -> list[ProjectSummary]:
    repo = get_repository()
    return [
        ProjectSummary(
            id=record.id,
            name=record.name,
            createdAt=record.created_at,
            productName=record.product.name,
        )
        for record in repo.list_projects()
    ]


@app.post("/projects", response_model=ProjectDetail)
def create_project(payload: CreateProjectRequest) -> ProjectDetail:
    script_ref = resolve_local_path(payload.scriptPath)
    voiceover_ref = resolve_local_path(payload.voiceoverPath)

    repo = get_repository()
    record = repo.create_project(
        name=payload.name,
        script_path=script_ref.absolutePath,
        voiceover_path=voiceover_ref.absolutePath,
        master_prompt=payload.masterPrompt,
        product_name=payload.product.name,
        product_brand=payload.product.brand,
        product_model=payload.product.model,
        product_url=payload.product.url,
        additional_urls=payload.product.additionalUrls,
    )

    create_project_directories(config, record.id)
    directories = project_directory_map(config, record.id)

    return ProjectDetail(
        id=record.id,
        name=record.name,
        createdAt=record.created_at,
        productName=record.product.name,
        scriptPath=record.script_path,
        voiceoverPath=record.voiceover_path,
        masterPrompt=record.master_prompt,
        product=ProductInput(
            name=record.product.name,
            brand=record.product.brand,
            model=record.product.model,
            url=record.product.url,
            additionalUrls=record.product.additional_urls,
        ),
        directories=ProjectDirectories(**directories),
    )


@app.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    repo = get_repository()
    record = repo.get_project(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Project not found")

    directories = project_directory_map(config, record.id)
    return ProjectDetail(
        id=record.id,
        name=record.name,
        createdAt=record.created_at,
        productName=record.product.name,
        scriptPath=record.script_path,
        voiceoverPath=record.voiceover_path,
        masterPrompt=record.master_prompt,
        product=ProductInput(
            name=record.product.name,
            brand=record.product.brand,
            model=record.product.model,
            url=record.product.url,
            additionalUrls=record.product.additional_urls,
        ),
        directories=ProjectDirectories(**directories),
    )
