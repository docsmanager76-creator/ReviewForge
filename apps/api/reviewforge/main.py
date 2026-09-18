from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from . import settings_store
from .config import load_config, ensure_data_dirs
from .db.database import get_connection, init_schema
from .db.repository import ProjectRecord, ProjectRepository
from .models.file_reference import resolve_local_path, store_uploaded_file
from .models.schemas import (
    AnalyzeVoiceResponse,
    CreateProjectRequest,
    DirectoryEntryResponse,
    DirectoryListingResponse,
    HealthResponse,
    JobResponse,
    NativeFolderPickerRequest,
    NativeFolderPickerResponse,
    ProjectDetail,
    ProjectDirectories,
    ProjectSummary,
    ProductInput,
    SettingsResponse,
    StorageStatus,
    UpdateDataDirRequest,
    VoiceAnalysisSummary,
)
from .pipeline.analyze_voice import VoiceAnalysisError, run_voice_analysis
from .pipeline.whisper_backend import WhisperBackend
from .util import folder_picker
from .util.filesystem import create_project_directories, get_storage_status, project_directory_map

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


def _project_detail(record: ProjectRecord) -> ProjectDetail:
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
    return _project_detail(record)


@app.post("/projects/with-files", response_model=ProjectDetail)
async def create_project_with_files(
    name: str = Form(...),
    productName: str = Form(...),
    brand: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    productUrl: Optional[str] = Form(None),
    masterPrompt: str = Form(""),
    script: UploadFile = File(...),
    voiceover: UploadFile = File(...),
) -> ProjectDetail:
    """The normal Create Project workflow: the browser reads the selected files' bytes and
    uploads them here — it never needs to know or type a Windows path. This is the UI-facing
    counterpart to the typed-path POST /projects above, which stays available for
    programmatic/CLI use and is what the Phase 0/1 test suite exercises."""
    repo = get_repository()
    record = repo.create_project(
        name=name,
        script_path="",  # placeholder; replaced below once the project directory exists
        voiceover_path="",
        master_prompt=masterPrompt,
        product_name=productName,
        product_brand=brand or None,
        product_model=model or None,
        product_url=productUrl or None,
        additional_urls=[],
    )

    project_root = create_project_directories(config, record.id)
    input_dir = project_root / "input"

    script_bytes = await script.read()
    voiceover_bytes = await voiceover.read()

    script_ref = store_uploaded_file(
        input_dir / _safe_upload_name(script.filename, default="script.md"), script.filename, script_bytes
    )
    voiceover_ref = store_uploaded_file(
        input_dir / _safe_upload_name(voiceover.filename, default="voiceover.wav"),
        voiceover.filename,
        voiceover_bytes,
    )

    repo.update_project_paths(record.id, script_ref.absolutePath, voiceover_ref.absolutePath)
    updated = repo.get_project(record.id)
    return _project_detail(updated)


def _safe_upload_name(original_filename: Optional[str], *, default: str) -> str:
    """Keeps the uploaded file's own extension when there is one (Whisper/ffmpeg care about
    it), otherwise falls back to a sane default name — never trusts the raw filename as a
    path (no directory separators are preserved)."""
    if not original_filename:
        return default
    name = Path(original_filename).name  # strips any path component the browser might send
    return name if name else default


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


def _settings_response() -> SettingsResponse:
    status = get_storage_status(config)
    return SettingsResponse(
        dataDir=str(config.data_dir),
        dataDirSource=config.data_dir_source,
        projectsDir=str(config.projects_dir),
        modelsDir=str(config.models_dir),
        status=StorageStatus(**status),
    )


@app.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return _settings_response()


@app.put("/settings/data-dir", response_model=SettingsResponse)
def update_data_dir(payload: UpdateDataDirRequest) -> SettingsResponse:
    """Changes where ReviewForge stores everything, from now on. Does NOT migrate existing
    projects from the old location — they remain there untouched; the app simply starts
    reading/writing at the new path (creating it, with a fresh app.db, if it doesn't exist
    yet). An env var override (REVIEWFORGE_DATA_DIR) always takes precedence over this."""
    global config

    new_path = Path(payload.path).expanduser()
    if not new_path.is_absolute():
        raise HTTPException(status_code=400, detail="Data directory must be an absolute path")

    settings_store.write_saved_data_dir(new_path)
    config = load_config()
    ensure_data_dirs(config)
    return _settings_response()


@app.get("/settings/browse", response_model=DirectoryListingResponse)
def browse_directory(path: Optional[str] = None) -> DirectoryListingResponse:
    """Backend-driven folder browser: the fallback used whenever a native OS dialog isn't
    available (non-Windows, no interactive desktop session, PowerShell missing). Lists
    subdirectories only — files aren't relevant when choosing a data folder."""
    try:
        entries = folder_picker.list_directory(path)
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parent = str(Path(path).parent) if path and Path(path).parent != Path(path) else None
    return DirectoryListingResponse(
        path=path,
        parent=parent,
        entries=[DirectoryEntryResponse(name=e.name, path=e.path) for e in entries],
    )


@app.post("/settings/browse-native", response_model=NativeFolderPickerResponse)
def browse_native(payload: NativeFolderPickerRequest) -> NativeFolderPickerResponse:
    """Tries to pop a real native OS folder dialog. Only ever meaningful on Windows with an
    interactive desktop session — see util/folder_picker.py for exactly why, and why this
    never fakes a result when it can't do that."""
    result = folder_picker.try_native_folder_picker(payload.initialPath)
    return NativeFolderPickerResponse(available=result.available, path=result.path, message=result.message)


@app.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    repo = get_repository()
    record = repo.get_project(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_detail(record)
