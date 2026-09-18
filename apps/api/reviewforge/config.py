"""
Local-first configuration for ReviewForge.

Precedence (highest wins): environment variables > the data directory's own config.json >
defaults. Secrets (LLM API keys) are NEVER read from config.json and never written to disk by
this module — they must be supplied as environment variables. config.json only ever holds
paths and non-secret model/provider choices. See _resolve_data_dir() below for how the data
directory *itself* is found, which is a separate, earlier resolution step.
"""
from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import settings_store

# The recommended/default location on Windows. Deliberately NOT under the user's home
# directory and NOT named "ReviewForgeData" — this is a fixed, easy-to-find root the app
# recommends out of the box; users remain free to point Settings -> Storage & Data (or
# REVIEWFORGE_DATA_DIR) at any other drive/folder instead.
WINDOWS_DEFAULT_DATA_DIR = "F:/ReviewForge"


def _default_data_dir() -> Path:
    if platform.system() == "Windows":
        return Path(WINDOWS_DEFAULT_DATA_DIR)
    # Non-Windows (dev sandbox, CI, macOS/Linux use): a drive letter default makes no sense,
    # so fall back to a home-relative folder as before.
    return Path.home() / "ReviewForgeData"


@dataclass
class WhisperConfig:
    model: str = "base"
    device: str = "cpu"


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-5"
    # api_key is intentionally NOT a field here — it is read directly from the
    # environment (see Config.llm_api_key) and must never be persisted to config.json.


@dataclass
class Config:
    data_dir: Path
    # Where data_dir's value came from — surfaced in the Settings UI so the user understands
    # why changing it in the UI might have no effect (an env var override always wins).
    data_dir_source: str = "default"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    node_path: str = "node"
    python_path: str = field(default_factory=lambda: os.environ.get("REVIEWFORGE_PYTHON_PATH", "python"))
    renderer_dir: str = "packages/renderer"
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @property
    def config_json_path(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def models_dir(self) -> Path:
        """Local Whisper model cache. faster-whisper/huggingface_hub will not re-download a
        model that is already present here."""
        return self.data_dir / "models"

    @property
    def llm_api_key(self) -> str | None:
        """Read directly from the environment on every access; never cached to disk."""
        return os.environ.get("REVIEWFORGE_LLM_API_KEY")

    def project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def to_public_dict(self) -> dict:
        """Serializable view used for config.json and API responses. Excludes secrets."""
        d = asdict(self)
        d["data_dir"] = str(self.data_dir)
        d.pop("llm_api_key", None)
        return d


def _load_config_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _resolve_data_dir() -> tuple[Path, str]:
    """Precedence: REVIEWFORGE_DATA_DIR env var (dev override) > the path saved via the
    Settings UI (~/.reviewforge/settings.json) > the built-in default (F:/ReviewForge on
    Windows; see WINDOWS_DEFAULT_DATA_DIR). The env var wins unconditionally so a developer's
    explicit override is never silently shadowed by a previously-saved UI choice."""
    env_value = os.environ.get("REVIEWFORGE_DATA_DIR")
    if env_value:
        return Path(env_value), "env"

    saved = settings_store.read_saved_data_dir()
    if saved is not None:
        return saved, "saved"

    return _default_data_dir(), "default"


def load_config() -> Config:
    data_dir, data_dir_source = _resolve_data_dir()
    file_values = _load_config_json(data_dir / "config.json")

    whisper_values = file_values.get("whisper", {})
    llm_values = file_values.get("llm", {})

    config = Config(
        data_dir=data_dir,
        data_dir_source=data_dir_source,
        ffmpeg_path=os.environ.get("REVIEWFORGE_FFMPEG_PATH", file_values.get("ffmpeg_path", "ffmpeg")),
        ffprobe_path=os.environ.get("REVIEWFORGE_FFPROBE_PATH", file_values.get("ffprobe_path", "ffprobe")),
        node_path=os.environ.get("REVIEWFORGE_NODE_PATH", file_values.get("node_path", "node")),
        python_path=os.environ.get("REVIEWFORGE_PYTHON_PATH", file_values.get("python_path", "python")),
        renderer_dir=os.environ.get("REVIEWFORGE_RENDERER_DIR", file_values.get("renderer_dir", "packages/renderer")),
        whisper=WhisperConfig(
            # REVIEWFORGE_WHISPER_MODEL is the namespaced form used elsewhere in this config
            # system; bare WHISPER_MODEL is also accepted since it's the name most Whisper
            # tooling documentation uses. The namespaced var wins if both are set.
            model=os.environ.get(
                "REVIEWFORGE_WHISPER_MODEL",
                os.environ.get("WHISPER_MODEL", whisper_values.get("model", "base")),
            ),
            device=os.environ.get("REVIEWFORGE_WHISPER_DEVICE", whisper_values.get("device", "cpu")),
        ),
        llm=LLMConfig(
            provider=os.environ.get("REVIEWFORGE_LLM_PROVIDER", llm_values.get("provider", "anthropic")),
            model=os.environ.get("REVIEWFORGE_LLM_MODEL", llm_values.get("model", "claude-sonnet-5")),
        ),
    )
    return config


def ensure_data_dirs(config: Config) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.projects_dir.mkdir(parents=True, exist_ok=True)
    config.models_dir.mkdir(parents=True, exist_ok=True)
    if not config.config_json_path.exists():
        config.config_json_path.write_text(json.dumps(config.to_public_dict(), indent=2), encoding="utf-8")
