"""End-to-end smoke test: simulates a real Windows machine with nothing configured yet
(no env var, no saved Settings choice) and confirms the whole stack -- /settings, project
creation, directory creation -- operates against F:/ReviewForge, not any excluded location."""
import sys


def test_settings_and_project_creation_use_windows_default(tmp_path, monkeypatch):
    monkeypatch.delenv("REVIEWFORGE_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    # Under pathlib's POSIX flavor (this test runs on Linux), "F:/ReviewForge" is not
    # recognized as absolute, so the app's real mkdir/sqlite-connect calls below would land
    # relative to the current directory. chdir into tmp_path so that side effect can never
    # touch the repo itself -- on real Windows this isn't a concern (WindowsPath treats
    # "F:/..." as absolute).
    monkeypatch.chdir(tmp_path)

    for name in list(sys.modules):
        if name == "reviewforge" or name.startswith("reviewforge."):
            del sys.modules[name]

    import reviewforge.config as config_module
    import reviewforge.main as main_module

    monkeypatch.setattr(config_module.platform, "system", lambda: "Windows")
    # main.py already built its module-level `config` at import time using the real OS --
    # rebuild it now that platform.system() is patched, exactly as PUT /settings/data-dir does.
    main_module.config = main_module.load_config()

    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as client:
        settings = client.get("/settings").json()
        assert settings["dataDir"] == "F:/ReviewForge"
        assert settings["dataDirSource"] == "default"
        assert settings["projectsDir"] == "F:/ReviewForge/projects"
        assert settings["modelsDir"] == "F:/ReviewForge/models"

        res = client.post(
            "/projects/with-files",
            data={"name": "DEWALT Test", "productName": "DEWALT 20V MAX XR Drill", "brand": "DEWALT"},
            files={
                "script": ("script.md", b"Sample script.", "text/markdown"),
                "voiceover": ("voiceover.wav", b"\x00", "audio/wav"),
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["directories"]["root"].startswith("F:/ReviewForge/projects/")
        assert body["scriptPath"].startswith("F:/ReviewForge/projects/")
        for excluded in ("ReviewForgeData", "D:/", "D:\\", "C:/Users", "C:\\Users"):
            assert excluded not in body["directories"]["root"]
