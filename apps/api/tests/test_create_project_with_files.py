from pathlib import Path


def test_create_project_with_files_uploads_and_writes_input_files(client):
    res = client.post(
        "/projects/with-files",
        data={
            "name": "DEWALT Test",
            "productName": "DEWALT 20V MAX XR Drill",
            "brand": "DEWALT",
            "model": "20V MAX XR Drill",
            "productUrl": "",
            "masterPrompt": "Edit this like a professional YouTube product review video.",
        },
        files={
            "script": ("script.md", b"This drill delivers up to 2,000 RPM.", "text/markdown"),
            "voiceover": ("voiceover.wav", b"\x00\x01\x02", "audio/wav"),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["name"] == "DEWALT Test"
    assert body["product"]["name"] == "DEWALT 20V MAX XR Drill"
    assert body["product"]["brand"] == "DEWALT"
    assert body["product"]["model"] == "20V MAX XR Drill"

    script_path = Path(body["scriptPath"])
    voiceover_path = Path(body["voiceoverPath"])
    assert script_path.exists()
    assert voiceover_path.exists()
    assert script_path.read_text(encoding="utf-8") == "This drill delivers up to 2,000 RPM."
    assert voiceover_path.read_bytes() == b"\x00\x01\x02"

    # Both uploaded files must land inside this project's own input/ folder.
    assert script_path.parent == Path(body["directories"]["input"])
    assert voiceover_path.parent == Path(body["directories"]["input"])

    for key in ("root", "input", "assets", "work", "output", "reports"):
        import os

        assert os.path.isdir(body["directories"][key]), f"missing directory: {key}"


def test_create_project_with_files_optional_fields_omitted(client):
    res = client.post(
        "/projects/with-files",
        data={
            "name": "Minimal Project",
            "productName": "Some Product",
        },
        files={
            "script": ("script.txt", b"Hello world.", "text/plain"),
            "voiceover": ("vo.mp3", b"\x00", "audio/mpeg"),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["masterPrompt"] == ""
    assert body["product"]["brand"] is None
    assert body["product"]["model"] is None


def test_create_project_with_files_requires_script_and_voiceover(client):
    res = client.post(
        "/projects/with-files",
        data={"name": "Missing Files", "productName": "X"},
    )
    assert res.status_code == 422


def test_uploaded_project_analyzable_end_to_end(client, monkeypatch):
    """The upload-created project must be usable by the exact same analyze/voice pipeline as
    a typed-path project -- Phase 1 must not care how the project's files arrived."""
    import reviewforge.main as main_module
    from reviewforge.pipeline.whisper_backend import RawSegment, RawTranscript, RawWord

    words_text = "this drill delivers up to two thousand rpm".split()
    words, t = [], 0.0
    for w in words_text:
        words.append(RawWord(word=w, start=t, end=t + 0.3))
        t += 0.3
    raw = RawTranscript(audio_duration=t, segments=[RawSegment(start=0.0, end=t, text=" ".join(words_text), words=words)])

    class _Backend:
        def transcribe(self, audio_path: str) -> RawTranscript:
            return raw

    monkeypatch.setattr(main_module, "WHISPER_BACKEND_FACTORY", lambda: _Backend())

    create_res = client.post(
        "/projects/with-files",
        data={"name": "Analyzable", "productName": "Widget"},
        files={
            "script": ("script.md", b"This drill delivers up to 2,000 RPM.", "text/markdown"),
            "voiceover": ("voiceover.wav", b"\x00", "audio/wav"),
        },
    )
    project_id = create_res.json()["id"]

    import time

    analyze_res = client.post(f"/projects/{project_id}/analyze/voice")
    job_id = analyze_res.json()["jobId"]

    deadline = time.time() + 5
    job = None
    while time.time() < deadline:
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.05)

    assert job["status"] == "succeeded", job
    assert job["result"]["sentenceCount"] == 1
