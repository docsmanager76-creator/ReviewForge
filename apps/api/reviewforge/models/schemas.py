from __future__ import annotations

from typing import List, Optional

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
