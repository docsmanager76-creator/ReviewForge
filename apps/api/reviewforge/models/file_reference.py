"""
FileReference mirrors packages/shared-types/src/fileReference.ts. It decouples "how a path
was obtained" from "where the file lives" so the pipeline never depends on the frontend's
input method. Today the only source produced is "local_path" (a typed absolute/relative path
in the local-first UI); a native file picker or a desktop wrapper (Electron dialog, etc.) can
be added later purely as new sources that still resolve down to an absolutePath here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

FileReferenceSource = Literal["local_path", "native_picker", "desktop_wrapper"]


class FileReference(BaseModel):
    source: FileReferenceSource
    absolutePath: str
    originalValue: Optional[str] = None
    displayName: Optional[str] = None


def resolve_local_path(value: str) -> FileReference:
    """Resolve a user-typed local path into a FileReference. Does not require the file to
    exist yet — callers decide whether existence is required for the operation at hand."""
    expanded = Path(value).expanduser()
    absolute = str(expanded.resolve()) if expanded.is_absolute() else str(Path.cwd() / expanded)
    return FileReference(source="local_path", absolutePath=absolute, originalValue=value)
