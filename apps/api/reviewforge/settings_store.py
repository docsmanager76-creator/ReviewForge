"""
Persists the user's chosen ReviewFogeData location outside of that location itself.

config.json normally lives *inside* the data directory (data_dir/config.json) — but if the
data directory's own path is user-configurable via the UI, something outside it has to
remember which path the user picked, or the app would have no way to find config.json on the
next launch. This tiny pointer file is that "something": a fixed, always-in-the-same-place
file that holds nothing but the chosen data directory path. It never holds secrets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def _settings_file_path() -> Path:
    return Path.home() / ".reviewforge" / "settings.json"


def read_saved_data_dir() -> Optional[Path]:
    path = _settings_file_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    data_dir = data.get("dataDir")
    return Path(data_dir) if data_dir else None


def write_saved_data_dir(data_dir: Path) -> None:
    path = _settings_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"dataDir": str(data_dir)}, indent=2), encoding="utf-8")
