"""Small FFmpeg/FFprobe utility: detect availability and probe media metadata. This is
intentionally minimal for Phase 0 — the full media pipeline (normalization, waveform
extraction, muxing) is a later phase."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from ..config import Config


@dataclass
class FfmpegAvailability:
    ffmpeg_found: bool
    ffprobe_found: bool
    ffmpeg_path: Optional[str]
    ffprobe_path: Optional[str]
    version: Optional[str]


def check_ffmpeg_available(config: Config) -> FfmpegAvailability:
    ffmpeg_path = shutil.which(config.ffmpeg_path) or (config.ffmpeg_path if _is_executable(config.ffmpeg_path) else None)
    ffprobe_path = shutil.which(config.ffprobe_path) or (config.ffprobe_path if _is_executable(config.ffprobe_path) else None)

    version = None
    if ffmpeg_path:
        try:
            result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True, timeout=10)
            version = result.stdout.splitlines()[0] if result.stdout else None
        except (OSError, subprocess.TimeoutExpired):
            version = None

    return FfmpegAvailability(
        ffmpeg_found=ffmpeg_path is not None,
        ffprobe_found=ffprobe_path is not None,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        version=version,
    )


def _is_executable(path: str) -> bool:
    import os

    return os.path.isfile(path) and os.access(path, os.X_OK)


def probe_media(config: Config, file_path: str) -> dict:
    """Run ffprobe on a local media file and return parsed JSON metadata (format + streams)."""
    ffprobe_path = shutil.which(config.ffprobe_path) or config.ffprobe_path
    result = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {file_path}: {result.stderr.strip()}")
    return json.loads(result.stdout)
