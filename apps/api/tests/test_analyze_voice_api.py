import time
from pathlib import Path

from reviewforge.pipeline.whisper_backend import RawSegment, RawTranscript, RawWord


def _matching_backend_factory():
    words_text = "this drill delivers up to two thousand rpm".split()
    words = []
    t = 0.0
    for w in words_text:
        words.append(RawWord(word=w, start=t, end=t + 0.3))
        t += 0.3
    raw = RawTranscript(audio_duration=t, segments=[RawSegment(start=0.0, end=t, text=" ".join(words_text), words=words)])

    class _Backend:
        def transcribe(self, audio_path: str) -> RawTranscript:
            return raw

    return lambda: _Backend()


def _wait_for_job(client, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        res = client.get(f"/jobs/{job_id}")
        assert res.status_code == 200
        last = res.json()
        if last["status"] in ("succeeded", "failed"):
            return last
        time.sleep(0.05)
    return last


def test_analyze_voice_endpoint_end_to_end(client, tmp_path, monkeypatch):
    import reviewforge.main as main_module

    monkeypatch.setattr(main_module, "WHISPER_BACKEND_FACTORY", _matching_backend_factory())

    script = tmp_path / "script.md"
    voiceover = tmp_path / "voiceover.wav"
    script.write_text("This drill delivers up to 2,000 RPM.", encoding="utf-8")
    voiceover.write_bytes(b"\x00")

    create_res = client.post(
        "/projects",
        json={
            "name": "Voice Test",
            "scriptPath": str(script),
            "voiceoverPath": str(voiceover),
            "masterPrompt": "Edit professionally.",
            "product": {"name": "Widget Pro"},
        },
    )
    assert create_res.status_code == 200
    project_id = create_res.json()["id"]

    analyze_res = client.post(f"/projects/{project_id}/analyze/voice")
    assert analyze_res.status_code == 200
    job_id = analyze_res.json()["jobId"]
    assert analyze_res.json()["status"] == "pending"

    job = _wait_for_job(client, job_id)
    assert job is not None
    assert job["status"] == "succeeded", job
    assert job["stage"] == "completed"
    assert job["progress"] == 100
    assert job["result"]["sentenceCount"] == 1

    summary_res = client.get(f"/projects/{project_id}/voice-analysis")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["sentenceCount"] == 1
    assert summary["transcriptStatus"] == "ready"

    project_dir = Path(create_res.json()["directories"]["root"])
    assert (project_dir / "work" / "transcript.json").exists()
    assert (project_dir / "work" / "sentences.json").exists()


def test_analyze_voice_missing_project_returns_404(client):
    res = client.post("/projects/does-not-exist/analyze/voice")
    assert res.status_code == 404


def test_voice_analysis_summary_404_before_analysis_runs(client, tmp_path):
    script = tmp_path / "script.md"
    voiceover = tmp_path / "voiceover.wav"
    script.write_text("Hello.", encoding="utf-8")
    voiceover.write_bytes(b"\x00")

    create_res = client.post(
        "/projects",
        json={
            "name": "No Analysis Yet",
            "scriptPath": str(script),
            "voiceoverPath": str(voiceover),
            "masterPrompt": "Edit professionally.",
            "product": {"name": "Widget Pro"},
        },
    )
    project_id = create_res.json()["id"]

    res = client.get(f"/projects/{project_id}/voice-analysis")
    assert res.status_code == 404
