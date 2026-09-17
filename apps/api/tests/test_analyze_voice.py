import json

import pytest

from reviewforge.pipeline.analyze_voice import VoiceAnalysisError, run_voice_analysis
from reviewforge.pipeline.whisper_backend import RawSegment, RawTranscript, RawWord

from .fixtures import build_fake_raw_transcript_wav_bytes


class FakeWhisperBackend:
    """Injected in place of FasterWhisperBackend — deterministic, no model download."""

    def __init__(self, raw_transcript: RawTranscript, error: Exception | None = None):
        self.raw_transcript = raw_transcript
        self.error = error
        self.calls = []

    def transcribe(self, audio_path: str) -> RawTranscript:
        self.calls.append(audio_path)
        if self.error:
            raise self.error
        return self.raw_transcript


def _matching_raw_transcript() -> RawTranscript:
    words_text = "this drill delivers up to two thousand rpm it also has a compact grip".split()
    words = []
    t = 0.0
    for w in words_text:
        words.append(RawWord(word=w, start=t, end=t + 0.4))
        t += 0.4
    return RawTranscript(
        audio_duration=t,
        segments=[RawSegment(start=0.0, end=t, text=" ".join(words_text), words=words)],
    )


@pytest.fixture()
def project_layout(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "input").mkdir(parents=True)
    script_path = project_dir / "input" / "script.md"
    voiceover_path = project_dir / "input" / "voiceover.wav"
    voiceover_path.write_bytes(build_fake_raw_transcript_wav_bytes())
    return project_dir, script_path, voiceover_path


def test_run_voice_analysis_writes_transcript_and_sentences(project_layout, tmp_config):
    project_dir, script_path, voiceover_path = project_layout
    script_path.write_text(
        "This drill delivers up to 2,000 RPM. It also has a compact grip.", encoding="utf-8"
    )
    backend = FakeWhisperBackend(_matching_raw_transcript())
    stages = []

    transcript, sentences_file = run_voice_analysis(
        tmp_config,
        project_dir,
        script_path,
        voiceover_path,
        whisper_backend=backend,
        progress_callback=lambda stage, pct: stages.append((stage, pct)),
    )

    assert backend.calls == [str(voiceover_path)]

    transcript_path = project_dir / "work" / "transcript.json"
    sentences_path = project_dir / "work" / "sentences.json"
    assert transcript_path.exists()
    assert sentences_path.exists()

    transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
    assert transcript_data["version"] == "1.0"
    assert transcript_data["audioDuration"] > 0
    assert len(transcript_data["segments"]) == 1

    sentences_data = json.loads(sentences_path.read_text(encoding="utf-8"))
    assert len(sentences_data["sentences"]) == 2
    first = sentences_data["sentences"][0]
    assert first["text"] == "This drill delivers up to 2,000 RPM."
    assert first["id"] == "sentence_001"
    assert first["contentType"] is None  # not fabricated in Phase 1

    assert stages[0][0] == "starting"
    assert stages[-1] == ("completed", 100)
    assert len(sentences_file.sentences) == 2


def test_missing_audio_raises(project_layout, tmp_config):
    project_dir, script_path, voiceover_path = project_layout
    script_path.write_text("Hello world.", encoding="utf-8")
    voiceover_path.unlink()

    with pytest.raises(VoiceAnalysisError, match="Voiceover file not found"):
        run_voice_analysis(
            tmp_config, project_dir, script_path, voiceover_path, whisper_backend=FakeWhisperBackend(_matching_raw_transcript())
        )


def test_missing_script_raises(project_layout, tmp_config):
    project_dir, script_path, voiceover_path = project_layout

    with pytest.raises(VoiceAnalysisError, match="Script file not found"):
        run_voice_analysis(
            tmp_config, project_dir, script_path, voiceover_path, whisper_backend=FakeWhisperBackend(_matching_raw_transcript())
        )


def test_empty_script_raises(project_layout, tmp_config):
    project_dir, script_path, voiceover_path = project_layout
    script_path.write_text("   \n\n  ", encoding="utf-8")

    with pytest.raises(VoiceAnalysisError, match="no parsable sentences"):
        run_voice_analysis(
            tmp_config, project_dir, script_path, voiceover_path, whisper_backend=FakeWhisperBackend(_matching_raw_transcript())
        )


def test_invalid_audio_backend_error_is_wrapped(project_layout, tmp_config):
    project_dir, script_path, voiceover_path = project_layout
    script_path.write_text("Hello world.", encoding="utf-8")
    backend = FakeWhisperBackend(_matching_raw_transcript(), error=RuntimeError("corrupt audio stream"))

    with pytest.raises(VoiceAnalysisError, match="Transcription failed"):
        run_voice_analysis(tmp_config, project_dir, script_path, voiceover_path, whisper_backend=backend)


def test_no_speech_segments_raises(project_layout, tmp_config):
    project_dir, script_path, voiceover_path = project_layout
    script_path.write_text("Hello world.", encoding="utf-8")
    backend = FakeWhisperBackend(RawTranscript(audio_duration=1.0, segments=[]))

    with pytest.raises(VoiceAnalysisError, match="no speech segments"):
        run_voice_analysis(tmp_config, project_dir, script_path, voiceover_path, whisper_backend=backend)


def test_alignment_confidence_handling_flows_through_to_sentences_file(project_layout, tmp_config):
    project_dir, script_path, voiceover_path = project_layout
    script_path.write_text("This sentence shares nothing with that recording at all.", encoding="utf-8")
    words_text = "completely unrelated audio content here".split()
    words = []
    t = 0.0
    for w in words_text:
        words.append(RawWord(word=w, start=t, end=t + 0.4))
        t += 0.4
    backend = FakeWhisperBackend(
        RawTranscript(audio_duration=t, segments=[RawSegment(start=0.0, end=t, text=" ".join(words_text), words=words)])
    )

    _, sentences_file = run_voice_analysis(tmp_config, project_dir, script_path, voiceover_path, whisper_backend=backend)

    assert len(sentences_file.sentences) == 1
    sentence = sentences_file.sentences[0]
    assert sentence.alignmentConfidence == 0.0
    assert sentence.needsReview is True
