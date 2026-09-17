"""
Phase 1 orchestration: script.md + voiceover.wav -> work/transcript.json + work/sentences.json.

    python -m reviewforge.pipeline.analyze_voice <project-id>

runs this directly against a project already created via the API/CLI, without needing the
frontend. This module contains no web-search, asset-matching, or visual-planning logic —
those are later phases.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from ..config import Config, ensure_data_dirs, load_config
from ..db.database import get_connection, init_schema
from ..db.repository import ProjectRepository
from .alignment import align_sentences
from .script_parser import parse_script_sentences
from .sentence_schema import Sentence, SentencesFile
from .transcript_schema import Transcript, transcript_from_raw
from .validation import validate_sentences
from .whisper_backend import FasterWhisperBackend, WhisperBackend

ProgressCallback = Callable[[str, int], None]

PROGRESS_STAGES = (
    "starting",
    "loading_model",
    "transcribing",
    "aligning_script",
    "validating",
    "completed",
    "failed",
)


#: Test seam for the CLI entry point: tests monkeypatch this to a factory returning a fixture
#: WhisperBackend so `python -m reviewforge.pipeline.analyze_voice <project-id>` can be
#: exercised deterministically, without downloading or running a real Whisper model. None
#: (the default, and always true for a real CLI invocation) uses FasterWhisperBackend.
CLI_WHISPER_BACKEND_FACTORY: Optional[Callable[[], WhisperBackend]] = None


class VoiceAnalysisError(Exception):
    """Raised for any Phase 1 failure (missing/invalid input, transcription failure, empty
    script). Callers (API endpoint, CLI) turn this into a job failure / non-zero exit rather
    than letting a raw exception surface."""


def _report(callback: Optional[ProgressCallback], stage: str, percent: int) -> None:
    if callback is not None:
        callback(stage, percent)


def run_voice_analysis(
    config: Config,
    project_dir: Path,
    script_path: Path,
    voiceover_path: Path,
    whisper_backend: Optional[WhisperBackend] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> Tuple[Transcript, SentencesFile]:
    _report(progress_callback, "starting", 0)

    if not voiceover_path.exists():
        raise VoiceAnalysisError(f"Voiceover file not found: {voiceover_path}")
    if not script_path.exists():
        raise VoiceAnalysisError(f"Script file not found: {script_path}")

    script_text = script_path.read_text(encoding="utf-8")
    sentence_texts = parse_script_sentences(script_text)
    if not sentence_texts:
        raise VoiceAnalysisError("Script contains no parsable sentences")

    _report(progress_callback, "loading_model", 10)
    backend = whisper_backend or FasterWhisperBackend(
        model_size=config.whisper.model,
        device=config.whisper.device,
        download_root=config.models_dir,
    )

    _report(progress_callback, "transcribing", 25)
    try:
        raw_transcript = backend.transcribe(str(voiceover_path))
    except Exception as exc:  # noqa: BLE001 - any backend failure becomes a VoiceAnalysisError
        raise VoiceAnalysisError(f"Transcription failed: {exc}") from exc

    if not raw_transcript.segments:
        raise VoiceAnalysisError("Whisper produced no speech segments for this audio file")

    transcript = transcript_from_raw(raw_transcript)

    work_dir = project_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    _write_json(work_dir / "transcript.json", transcript.model_dump())

    _report(progress_callback, "aligning_script", 60)
    alignments = align_sentences(sentence_texts, transcript)

    sentences: List[Sentence] = [
        Sentence(
            id=f"sentence_{i + 1:03d}",
            index=i,
            text=text,
            startTime=alignment.startTime,
            endTime=alignment.endTime,
            alignmentConfidence=alignment.confidence,
            needsReview=alignment.needsReview,
        )
        for i, (text, alignment) in enumerate(zip(sentence_texts, alignments))
    ]

    _report(progress_callback, "validating", 85)
    validate_sentences(sentences, transcript.audioDuration)

    sentences_file = SentencesFile(sentences=sentences)
    _write_json(work_dir / "sentences.json", sentences_file.model_dump())

    _report(progress_callback, "completed", 100)
    return transcript, sentences_file


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Usage: python -m reviewforge.pipeline.analyze_voice <project-id>", file=sys.stderr)
        return 1
    project_id = argv[0]

    config = load_config()
    ensure_data_dirs(config)
    conn = get_connection(config.db_path)
    init_schema(conn)
    repo = ProjectRepository(conn)
    record = repo.get_project(project_id)
    if record is None:
        print(f"Project not found: {project_id}", file=sys.stderr)
        return 1

    project_dir = config.project_dir(project_id)

    def progress(stage: str, percent: int) -> None:
        print(f"[{percent:3d}%] {stage}")

    backend = CLI_WHISPER_BACKEND_FACTORY() if CLI_WHISPER_BACKEND_FACTORY is not None else None

    try:
        run_voice_analysis(
            config,
            project_dir,
            Path(record.script_path),
            Path(record.voiceover_path),
            whisper_backend=backend,
            progress_callback=progress,
        )
    except VoiceAnalysisError as exc:
        print(f"Voice analysis failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {project_dir / 'work' / 'transcript.json'}")
    print(f"Wrote {project_dir / 'work' / 'sentences.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
