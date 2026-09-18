"""
Local Whisper-compatible transcription backend.

Audio never leaves the machine: the real backend (FasterWhisperBackend) runs
faster-whisper in-process against a local model cache under the configured data
directory's models/ subfolder (e.g. F:/ReviewForge/models/ on the recommended Windows
default), and faster-whisper itself is only imported lazily inside
_load_model() so that importing this module — and running the rest of the test suite —
never requires the (optional, heavy) faster-whisper package to be installed.

WhisperBackend is a Protocol so tests can inject a fake/fixture-based backend instead of
running real transcription.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol


@dataclass
class RawWord:
    word: str
    start: float
    end: float
    probability: Optional[float] = None


@dataclass
class RawSegment:
    start: float
    end: float
    text: str
    words: List[RawWord] = field(default_factory=list)
    avg_logprob: Optional[float] = None


@dataclass
class RawTranscript:
    audio_duration: float
    segments: List[RawSegment]


class WhisperBackend(Protocol):
    def transcribe(self, audio_path: str) -> RawTranscript: ...


class FasterWhisperBackend:
    """Real backend. Requires the optional `faster-whisper` package
    (see apps/api/requirements-whisper.txt) — not imported until transcribe() is called."""

    def __init__(self, model_size: str, device: str, download_root: Path):
        self.model_size = model_size
        self.device = device
        self.download_root = download_root
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:  # pragma: no cover - exercised only without the optional dep
                raise RuntimeError(
                    "faster-whisper is not installed. Install it with "
                    "`pip install -r requirements-whisper.txt` to run real voice analysis."
                ) from exc

            self.download_root.mkdir(parents=True, exist_ok=True)
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                download_root=str(self.download_root),
            )
        return self._model

    def transcribe(self, audio_path: str) -> RawTranscript:
        model = self._load_model()
        segments_iter, info = model.transcribe(audio_path, word_timestamps=True)

        segments: List[RawSegment] = []
        for seg in segments_iter:
            words = [
                RawWord(
                    word=w.word.strip(),
                    start=w.start,
                    end=w.end,
                    probability=getattr(w, "probability", None),
                )
                for w in (seg.words or [])
            ]
            segments.append(
                RawSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    words=words,
                    avg_logprob=getattr(seg, "avg_logprob", None),
                )
            )

        audio_duration = getattr(info, "duration", None)
        if audio_duration is None:
            audio_duration = segments[-1].end if segments else 0.0

        return RawTranscript(audio_duration=audio_duration, segments=segments)
