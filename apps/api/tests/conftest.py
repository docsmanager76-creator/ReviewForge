import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("REVIEWFORGE_DATA_DIR", str(tmp_path / "ReviewForgeData"))

    # Reload modules so config.load_config() picks up the patched env var, since
    # reviewforge.main evaluates load_config() once at import time.
    for name in list(sys.modules):
        if name == "reviewforge" or name.startswith("reviewforge."):
            del sys.modules[name]

    from fastapi.testclient import TestClient
    from reviewforge.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    """A Config pointed at an isolated temp data dir, for pipeline tests that don't need the
    full FastAPI app (test_analyze_voice.py, test_alignment.py, etc.)."""
    monkeypatch.setenv("REVIEWFORGE_DATA_DIR", str(tmp_path / "ReviewForgeData"))
    from reviewforge.config import ensure_data_dirs, load_config

    config = load_config()
    ensure_data_dirs(config)
    return config
