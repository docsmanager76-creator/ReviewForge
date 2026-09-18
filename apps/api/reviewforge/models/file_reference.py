"""
FileReference mirrors packages/shared-types/src/fileReference.ts. It decouples "how a path
was obtained" from "where the file lives" so the pipeline never depends on the frontend's
input method. Sources produced so far: "local_path" (a typed absolute/relative path) and
"browser_upload" (the browser read a file's bytes and the backend wrote them into the
project's input/ folder — see main.py's POST /projects/with-files). A native file picker or a
desktop wrapper (Electron dialog, etc.) can be added later purely as new sources that still
resolve down to an absolutePath here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

FileReferenceSource = Literal["local_path", "browser_upload", "native_picker", "desktop_wrapper"]


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


def store_uploaded_file(destination: Path, original_filename: Optional[str], content: bytes) -> FileReference:
    """Writes browser-uploaded file content to `destination` (an exact path chosen by the
    caller, inside the project's input/ folder) and returns a FileReference recording that
    this file arrived via browser upload, not a typed path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return FileReference(
        source="browser_upload",
        absolutePath=str(destination.resolve()),
        originalValue=original_filename,
        displayName=original_filename,
    )
