"""Exercises `python -m reviewforge.pipeline.analyze_voice <project-id>` in-process (calling
main() directly rather than spawning a subprocess) with a fixture Whisper backend injected via
CLI_WHISPER_BACKEND_FACTORY, so it never downloads or runs a real model."""
import json

from reviewforge.pipeline import analyze_voice as analyze_voice_module
from reviewforge.pipeline.whisper_backend import RawSegment, RawTranscript, RawWord


def _fixture_backend_factory():
    words_text = "this drill delivers up to two thousand rpm".split()
    words, t = [], 0.0
    for w in words_text:
        words.append(RawWord(word=w, start=t, end=t + 0.3))
        t += 0.3
    raw = RawTranscript(audio_duration=t, segments=[RawSegment(start=0.0, end=t, text=" ".join(words_text), words=words)])

    class _Backend:
        def transcribe(self, audio_path: str) -> RawTranscript:
            return raw

    return lambda: _Backend()


def test_cli_produces_transcript_and_sentences(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("REVIEWFORGE_DATA_DIR", str(tmp_path / "ReviewForgeData"))
    monkeypatch.setattr(analyze_voice_module, "CLI_WHISPER_BACKEND_FACTORY", _fixture_backend_factory())

    from reviewforge.config import ensure_data_dirs, load_config
    from reviewforge.db.database import get_connection, init_schema
    from reviewforge.db.repository import ProjectRepository

    config = load_config()
    ensure_data_dirs(config)
    conn = get_connection(config.db_path)
    init_schema(conn)
    repo = ProjectRepository(conn)

    script = tmp_path / "script.md"
    voiceover = tmp_path / "voiceover.wav"
    script.write_text("This drill delivers up to 2,000 RPM.", encoding="utf-8")
    voiceover.write_bytes(b"\x00")

    record = repo.create_project(
        name="CLI Test",
        script_path=str(script),
        voiceover_path=str(voiceover),
        master_prompt="Edit professionally.",
        product_name="Widget Pro",
        product_brand=None,
        product_model=None,
        product_url=None,
        additional_urls=[],
    )

    exit_code = analyze_voice_module.main([record.id])
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "completed" in out or "100%" in out

    project_dir = config.project_dir(record.id)
    transcript_path = project_dir / "work" / "transcript.json"
    sentences_path = project_dir / "work" / "sentences.json"
    assert transcript_path.exists()
    assert sentences_path.exists()

    sentences = json.loads(sentences_path.read_text(encoding="utf-8"))["sentences"]
    assert len(sentences) == 1
    assert sentences[0]["text"] == "This drill delivers up to 2,000 RPM."


def test_cli_unknown_project_returns_error_exit_code(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("REVIEWFORGE_DATA_DIR", str(tmp_path / "ReviewForgeData"))
    exit_code = analyze_voice_module.main(["does-not-exist"])
    assert exit_code == 1
    assert "not found" in capsys.readouterr().err


def test_cli_requires_exactly_one_argument(capsys):
    assert analyze_voice_module.main([]) == 1
    assert analyze_voice_module.main(["a", "b"]) == 1
