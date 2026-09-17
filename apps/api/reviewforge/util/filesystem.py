"""Local project directory management. Every project gets a self-contained folder tree under
ReviewForgeData/projects/<project-id>/ so a project can be backed up or moved independently of
the ReviewForge codebase."""
from __future__ import annotations

from pathlib import Path

from ..config import Config

SUBDIRS = [
    "input",
    "assets",
    "assets/images",
    "assets/video",
    "assets/graphics",
    "work",
    "output",
]


def create_project_directories(config: Config, project_id: str) -> Path:
    root = config.project_dir(project_id)
    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def project_directory_map(config: Config, project_id: str) -> dict:
    root = config.project_dir(project_id)
    return {
        "root": str(root),
        "input": str(root / "input"),
        "assets": str(root / "assets"),
        "work": str(root / "work"),
        "output": str(root / "output"),
    }
