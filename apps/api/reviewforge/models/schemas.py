from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    url: Optional[str] = None
    additionalUrls: List[str] = Field(default_factory=list)


class CreateProjectRequest(BaseModel):
    name: str
    scriptPath: str
    voiceoverPath: str
    masterPrompt: str
    product: ProductInput


class ProjectDirectories(BaseModel):
    root: str
    input: str
    assets: str
    work: str
    output: str
    reports: str


class ProjectSummary(BaseModel):
    id: str
    name: str
    createdAt: str
    productName: str


class ProjectDetail(ProjectSummary):
    scriptPath: str
    voiceoverPath: str
    masterPrompt: str
    product: ProductInput
    directories: ProjectDirectories


class HealthResponse(BaseModel):
    status: str
    version: str


class AnalyzeVoiceResponse(BaseModel):
    jobId: str
    status: str


class JobResponse(BaseModel):
    id: str
    projectId: str
    type: str
    status: str
    stage: Optional[str] = None
    progress: int
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class VoiceAnalysisSummary(BaseModel):
    audioDuration: float
    sentenceCount: int
    needsReviewCount: int
    transcriptStatus: str
    alignmentStatus: str


class StorageStatus(BaseModel):
    exists: bool
    writable: bool
    freeBytes: Optional[int] = None
    totalBytes: Optional[int] = None


class SettingsResponse(BaseModel):
    dataDir: str
    dataDirSource: str  # "env" | "saved" | "default"
    projectsDir: str
    modelsDir: str
    status: StorageStatus


class UpdateDataDirRequest(BaseModel):
    path: str


class DirectoryEntryResponse(BaseModel):
    name: str
    path: str


class DirectoryListingResponse(BaseModel):
    path: Optional[str] = None
    parent: Optional[str] = None
    entries: List[DirectoryEntryResponse]


class NativeFolderPickerRequest(BaseModel):
    initialPath: Optional[str] = None


class NativeFolderPickerResponse(BaseModel):
    available: bool
    path: Optional[str] = None
    message: Optional[str] = None
