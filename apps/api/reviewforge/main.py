from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import load_config, ensure_data_dirs
from .db.database import get_connection, init_schema
from .db.repository import ProjectRepository
from .models.file_reference import resolve_local_path
from .models.schemas import (
    AnalyzeVoiceResponse,
    CreateProjectRequest,
    HealthResponse,
    JobResponse,
    ProjectDetail,
    ProjectDirectories,
    ProjectSummary,
    ProductInput,
    VoiceAnalysisSummary,
)
from .pipeline.analyze_voice import VoiceAnalysisError, run_voice_analysis
from .pipeline.whisper_backend import WhisperBackend
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


# Test seam: tests monkeypatch this to inject a fake WhisperBackend instead of running real
# (slow, model-download-requiring) transcription through the API. None means "use the real
# FasterWhisperBackend", which is run_voice_analysis's own default.
WHISPER_BACKEND_FACTORY: Optional[Callable[[], WhisperBackend]] = None


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


def _run_voice_analysis_job(project_id: str, job_id: str, script_path: str, voiceover_path: str) -> None:
    """Runs in a FastAPI BackgroundTask: no queue/worker process, per the local-first,
    no-Redis/no-Celery architecture rule — this is a single-user local tool."""
    conn = get_connection(config.db_path)
    init_schema(conn)
    job_repo = ProjectRepository(conn)

    def progress(stage: str, percent: int) -> None:
        job_repo.update_job(job_id, status="running", stage=stage, progress=percent)

    backend = WHISPER_BACKEND_FACTORY() if WHISPER_BACKEND_FACTORY is not None else None

    try:
        job_repo.update_job(job_id, status="running", stage="starting", progress=0)
        transcript, sentences_file = run_voice_analysis(
            config,
            config.project_dir(project_id),
            Path(script_path),
            Path(voiceover_path),
            whisper_backend=backend,
            progress_callback=progress,
        )
        needs_review_count = sum(1 for s in sentences_file.sentences if s.needsReview)
        job_repo.update_job(
            job_id,
            status="succeeded",
            stage="completed",
            progress=100,
            result={
                "audioDuration": transcript.audioDuration,
                "sentenceCount": len(sentences_file.sentences),
                "needsReviewCount": needs_review_count,
            },
        )
    except VoiceAnalysisError as exc:
        job_repo.update_job(job_id, status="failed", stage="failed", progress=0, error=str(exc))


@app.post("/projects/{project_id}/analyze/voice", response_model=AnalyzeVoiceResponse)
def analyze_voice(project_id: str, background_tasks: BackgroundTasks) -> AnalyzeVoiceResponse:
    repo = get_repository()
    record = repo.get_project(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Project not found")

    job_id = repo.create_job(project_id, "analyze_voice")
    background_tasks.add_task(
        _run_voice_analysis_job, project_id, job_id, record.script_path, record.voiceover_path
    )
    return AnalyzeVoiceResponse(jobId=job_id, status="pending")


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    repo = get_repository()
    job = repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        id=job.id,
        projectId=job.project_id,
        type=job.type,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        error=job.error,
        result=job.result,
    )


@app.get("/projects/{project_id}/voice-analysis", response_model=VoiceAnalysisSummary)
def get_voice_analysis(project_id: str) -> VoiceAnalysisSummary:
    project_dir = config.project_dir(project_id)
    transcript_path = project_dir / "work" / "transcript.json"
    sentences_path = project_dir / "work" / "sentences.json"

    if not transcript_path.exists() or not sentences_path.exists():
        raise HTTPException(status_code=404, detail="Voice analysis has not been run for this project yet")

    transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
    sentences_data = json.loads(sentences_path.read_text(encoding="utf-8"))
    sentences = sentences_data.get("sentences", [])
    needs_review_count = sum(1 for s in sentences if s.get("needsReview"))

    return VoiceAnalysisSummary(
        audioDuration=transcript_data.get("audioDuration", 0.0),
        sentenceCount=len(sentences),
        needsReviewCount=needs_review_count,
        transcriptStatus="ready",
        alignmentStatus="needs_review" if needs_review_count > 0 else "ok",
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
