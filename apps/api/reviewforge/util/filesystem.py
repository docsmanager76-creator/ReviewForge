"""Local project directory management. Every project gets a self-contained folder tree under
ReviewForgeData/projects/<project-id>/ so a project can be backed up or moved independently of
the ReviewForge codebase."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from ..config import Config

SUBDIRS = [
    "input",
    "assets",
    "assets/images",
    "assets/video",
    "assets/graphics",
    "work",
    "output",
    "reports",
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
        "reports": str(root / "reports"),
    }


def get_storage_status(config: Config) -> dict:
    """Existence/writability/free-space for the Settings UI. Never raises — a permission
    error or a not-yet-created directory is reported as a status, not an exception."""
    data_dir = config.data_dir
    exists = data_dir.exists()
    writable = False
    free_bytes: Optional[int] = None
    total_bytes: Optional[int] = None

    probe_dir = data_dir if exists else data_dir.parent
    try:
        usage = shutil.disk_usage(probe_dir if probe_dir.exists() else Path.cwd())
        free_bytes, total_bytes = usage.free, usage.total
    except OSError:
        pass

    if exists:
        try:
            probe_file = data_dir / ".reviewforge_write_test"
            probe_file.write_text("ok", encoding="utf-8")
            probe_file.unlink()
            writable = True
        except OSError:
            writable = False

    return {
        "exists": exists,
        "writable": writable,
        "freeBytes": free_bytes,
        "totalBytes": total_bytes,
    }
