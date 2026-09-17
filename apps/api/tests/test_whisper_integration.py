"""
Optional integration test that exercises the REAL faster-whisper backend. Skipped by default —
it requires the faster-whisper package installed and downloads/loads an actual model, which is
slow and depends on network access on first run. Enable explicitly with:

    REVIEWFORGE_RUN_WHISPER_INTEGRATION_TEST=1 pytest tests/test_whisper_integration.py

This only checks that the real backend runs end-to-end without crashing on a short silent
clip — it is a smoke test, not a transcription-accuracy test (silence has no speech to
transcribe correctly).
"""
import os
import struct
import wave

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("REVIEWFORGE_RUN_WHISPER_INTEGRATION_TEST") != "1",
    reason="Set REVIEWFORGE_RUN_WHISPER_INTEGRATION_TEST=1 to run the real Whisper integration test",
)


def _write_silent_wav(path, duration_seconds: float = 2.0, sample_rate: int = 16000) -> None:
    num_samples = int(duration_seconds * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack("<%dh" % num_samples, *([0] * num_samples)))


def test_real_faster_whisper_backend_runs_without_crashing(tmp_path, tmp_config):
    faster_whisper = pytest.importorskip("faster_whisper")
    from reviewforge.pipeline.whisper_backend import FasterWhisperBackend

    audio_path = tmp_path / "silence.wav"
    _write_silent_wav(audio_path)

    backend = FasterWhisperBackend(model_size="tiny", device="cpu", download_root=tmp_config.models_dir)
    raw_transcript = backend.transcribe(str(audio_path))

    assert raw_transcript.audio_duration > 0
    assert isinstance(raw_transcript.segments, list)
