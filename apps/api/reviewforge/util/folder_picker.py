"""
Folder selection for the Settings UI, without ever pretending a browser can reach the
filesystem on its own.

Two mechanisms, in order of preference:

1. try_native_folder_picker() — shells out to a native OS dialog. On Windows this pops a real
   Explorer "Browse For Folder" window via a one-line PowerShell/.NET call. This only works
   because ReviewForge's backend and its browser UI run on the SAME physical machine (the
   whole point of local-first) and there is an interactive desktop session to show a dialog
   in. It correctly reports unavailable (never fakes a result) when: not on Windows, no
   PowerShell, no interactive desktop (e.g. a headless/service install), or the user cancels.

2. list_drives() / list_directory() — a backend-driven directory browser as a universal
   fallback. The backend has ordinary local filesystem access (it's not a remote server), so
   it can simply list directories for the frontend to render as a click-through browser. This
   always works, on any OS, with no native dialog involved.
"""
from __future__ import annotations

import platform
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class DirectoryEntry:
    name: str
    path: str


@dataclass
class NativePickerResult:
    available: bool
    path: Optional[str]
    message: Optional[str]


_NATIVE_DIALOG_TIMEOUT_SECONDS = 300  # user may sit in the dialog for a while

_POWERSHELL_FOLDER_DIALOG_SCRIPT = """
Add-Type -AssemblyName System.Windows.Forms | Out-Null
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Select the ReviewForgeData folder'
if (-not [string]::IsNullOrWhiteSpace($env:REVIEWFORGE_INITIAL_PATH)) {
    $dialog.SelectedPath = $env:REVIEWFORGE_INITIAL_PATH
}
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $dialog.SelectedPath
}
"""


def try_native_folder_picker(initial_path: Optional[str] = None) -> NativePickerResult:
    if platform.system() != "Windows":
        return NativePickerResult(
            available=False, path=None, message="Native folder dialog is only available on Windows."
        )

    try:
        import os

        env = os.environ.copy()
        if initial_path:
            env["REVIEWFORGE_INITIAL_PATH"] = initial_path

        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _POWERSHELL_FOLDER_DIALOG_SCRIPT],
            capture_output=True,
            text=True,
            timeout=_NATIVE_DIALOG_TIMEOUT_SECONDS,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return NativePickerResult(
            available=False, path=None, message=f"Could not launch native folder dialog: {exc}"
        )

    if result.returncode != 0:
        return NativePickerResult(
            available=False,
            path=None,
            message="Native folder dialog failed (no interactive desktop session, or PowerShell unavailable).",
        )

    selected = result.stdout.strip()
    if not selected:
        # Dialog opened and the user cancelled — not an error, just no selection.
        return NativePickerResult(available=True, path=None, message="No folder selected (cancelled).")

    return NativePickerResult(available=True, path=selected, message=None)


def list_drives() -> List[DirectoryEntry]:
    if platform.system() == "Windows":
        drives = []
        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            if Path(root).exists():
                drives.append(DirectoryEntry(name=root, path=root))
        return drives
    # POSIX dev/test environments: the filesystem root is the only sensible starting point.
    return [DirectoryEntry(name="/", path="/")]


def list_directory(path: Optional[str]) -> List[DirectoryEntry]:
    """Subdirectories only (files are irrelevant to choosing a data folder). Returns the
    drive/root list when path is None."""
    if not path:
        return list_drives()

    target = Path(path)
    if not target.exists() or not target.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    entries = []
    try:
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir():
                entries.append(DirectoryEntry(name=child.name, path=str(child)))
    except PermissionError:
        pass  # Skip unreadable directories rather than failing the whole listing.
    return entries
