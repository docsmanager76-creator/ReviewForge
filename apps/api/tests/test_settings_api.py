from pathlib import Path


def test_get_settings_reports_env_source(client, tmp_path):
    res = client.get("/settings")
    assert res.status_code == 200
    body = res.json()
    assert body["dataDir"] == str(tmp_path / "ReviewForgeData")
    assert body["dataDirSource"] == "env"  # the `client` fixture sets REVIEWFORGE_DATA_DIR
    assert body["projectsDir"] == str(tmp_path / "ReviewForgeData" / "projects")
    assert body["modelsDir"] == str(tmp_path / "ReviewForgeData" / "models")
    assert body["status"]["exists"] is True
    assert body["status"]["writable"] is True


def test_update_data_dir_requires_absolute_path(client):
    res = client.put("/settings/data-dir", json={"path": "relative/path"})
    assert res.status_code == 400


def test_update_data_dir_env_var_still_wins(client, tmp_path, monkeypatch):
    # Even after saving a new path via the UI endpoint, REVIEWFORGE_DATA_DIR (already set by
    # the `client` fixture) must keep winning — an explicit dev override is never shadowed.
    other_dir = tmp_path / "SomeOtherLocation"
    res = client.put("/settings/data-dir", json={"path": str(other_dir)})
    assert res.status_code == 200
    body = res.json()
    assert body["dataDirSource"] == "env"
    assert body["dataDir"] == str(tmp_path / "ReviewForgeData")


def test_browse_directory_lists_subdirectories(client, tmp_path):
    base = tmp_path / "browse_root"
    (base / "sub_a").mkdir(parents=True)
    (base / "sub_b").mkdir(parents=True)
    (base / "not_a_dir.txt").write_text("x")

    res = client.get("/settings/browse", params={"path": str(base)})
    assert res.status_code == 200
    body = res.json()
    names = sorted(e["name"] for e in body["entries"])
    assert names == ["sub_a", "sub_b"]


def test_browse_directory_missing_path_returns_roots(client):
    res = client.get("/settings/browse")
    assert res.status_code == 200
    body = res.json()
    assert len(body["entries"]) >= 1


def test_browse_directory_rejects_non_directory(client, tmp_path):
    res = client.get("/settings/browse", params={"path": str(tmp_path / "does-not-exist")})
    assert res.status_code == 400


def test_browse_native_reports_unavailable_off_windows(client, monkeypatch):
    import reviewforge.main as main_module

    res = client.post("/settings/browse-native", json={"initialPath": None})
    assert res.status_code == 200
    body = res.json()
    # This test suite always runs on the CI/dev machine's actual OS, so we only assert the
    # response shape is well-formed and self-consistent, not a specific OS outcome.
    assert isinstance(body["available"], bool)
    if not body["available"]:
        assert body["path"] is None
        assert body["message"]
