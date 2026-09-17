import os
from pathlib import Path


def _create_payload(tmp_path: Path) -> dict:
    script = tmp_path / "script.md"
    voiceover = tmp_path / "voiceover.wav"
    script.write_text("Hello world script.")
    voiceover.write_bytes(b"\x00")

    return {
        "name": "Test Review",
        "scriptPath": str(script),
        "voiceoverPath": str(voiceover),
        "masterPrompt": "Edit like a professional YouTuber.",
        "product": {
            "name": "Widget Pro",
            "brand": "Acme",
            "model": "WP-2000",
            "url": "https://example.com/widget-pro",
            "additionalUrls": ["https://example.com/widget-pro/specs"],
        },
    }


def test_create_and_list_projects(client, tmp_path):
    payload = _create_payload(tmp_path)
    res = client.post("/projects", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["name"] == "Test Review"
    assert body["productName"] == "Widget Pro"
    assert body["product"]["brand"] == "Acme"
    assert body["product"]["url"] == "https://example.com/widget-pro"
    assert body["scriptPath"] == str(Path(payload["scriptPath"]).resolve())

    project_id = body["id"]
    for key in ("root", "input", "assets", "work", "output"):
        assert os.path.isdir(body["directories"][key]), f"missing directory: {key}"
    assert os.path.isdir(os.path.join(body["directories"]["assets"], "images"))
    assert os.path.isdir(os.path.join(body["directories"]["assets"], "video"))
    assert os.path.isdir(os.path.join(body["directories"]["assets"], "graphics"))

    list_res = client.get("/projects")
    assert list_res.status_code == 200
    projects = list_res.json()
    assert any(p["id"] == project_id for p in projects)


def test_get_project_not_found(client):
    res = client.get("/projects/does-not-exist")
    assert res.status_code == 404


def test_get_project_roundtrip(client, tmp_path):
    payload = _create_payload(tmp_path)
    create_res = client.post("/projects", json=payload)
    project_id = create_res.json()["id"]

    get_res = client.get(f"/projects/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == project_id
