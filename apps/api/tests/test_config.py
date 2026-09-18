from pathlib import Path


def test_config_json_created(client, tmp_path):
    from reviewforge.config import load_config

    config = load_config()
    assert config.config_json_path.exists()
    assert config.data_dir == tmp_path / "ReviewForgeData"


def test_llm_api_key_never_persisted(client, monkeypatch):
    monkeypatch.setenv("REVIEWFORGE_LLM_API_KEY", "sk-test-secret")
    from reviewforge.config import load_config

    config = load_config()
    assert config.llm_api_key == "sk-test-secret"
    contents = config.config_json_path.read_text(encoding="utf-8")
    assert "sk-test-secret" not in contents
    assert "llm_api_key" not in config.to_public_dict()


def test_default_data_dir_on_windows_is_f_reviewforge(tmp_path, monkeypatch):
    """The recommended/default location on Windows must be exactly F:\\ReviewForge — not
    D:\\ReviewForgeData, not F:\\ReviewForgeData, and not anywhere under C:\\Users\\...

    Note: under pathlib's POSIX flavor (this test runs on Linux), a "F:/..." string is not
    recognized as absolute, so anything that calls .mkdir()/.resolve() on it would land
    relative to the current directory — chdir into tmp_path so no such side effect can ever
    touch the repo itself. On real Windows, WindowsPath correctly treats "F:/..." as absolute
    and this concern doesn't arise.
    """
    monkeypatch.delenv("REVIEWFORGE_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # keep the non-Windows pointer-file path isolated
    monkeypatch.chdir(tmp_path)

    import reviewforge.config as config_module

    monkeypatch.setattr(config_module.platform, "system", lambda: "Windows")

    config = config_module.load_config()
    assert str(config.data_dir) == "F:/ReviewForge"
    assert config.data_dir_source == "default"


def test_default_data_dir_off_windows_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("REVIEWFORGE_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    import reviewforge.config as config_module

    monkeypatch.setattr(config_module.platform, "system", lambda: "Linux")

    config = config_module.load_config()
    assert config.data_dir == tmp_path / "ReviewForgeData"


def test_windows_default_does_not_use_excluded_locations(tmp_path, monkeypatch):
    monkeypatch.delenv("REVIEWFORGE_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    import reviewforge.config as config_module

    monkeypatch.setattr(config_module.platform, "system", lambda: "Windows")

    resolved = str(config_module.load_config().data_dir)
    assert "ReviewForgeData" not in resolved
    assert "D:" not in resolved
    assert "C:/Users" not in resolved and "C:\\Users" not in resolved
