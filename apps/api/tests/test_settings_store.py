from pathlib import Path

from reviewforge import settings_store


def test_read_saved_data_dir_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert settings_store.read_saved_data_dir() is None


def test_write_then_read_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / "D_drive_simulation" / "ReviewForgeData"

    settings_store.write_saved_data_dir(target)

    assert settings_store.read_saved_data_dir() == target
    pointer_file = tmp_path / ".reviewforge" / "settings.json"
    assert pointer_file.exists()
    assert str(target) in pointer_file.read_text(encoding="utf-8")


def test_read_saved_data_dir_survives_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    pointer_file = tmp_path / ".reviewforge" / "settings.json"
    pointer_file.parent.mkdir(parents=True)
    pointer_file.write_text("{not valid json", encoding="utf-8")

    assert settings_store.read_saved_data_dir() is None


def test_config_uses_saved_pointer_when_no_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("REVIEWFORGE_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / "ChosenLocation"
    settings_store.write_saved_data_dir(target)

    from reviewforge.config import load_config

    config = load_config()
    assert config.data_dir == target
    assert config.data_dir_source == "saved"


def test_config_falls_back_to_default_with_nothing_set(tmp_path, monkeypatch):
    monkeypatch.delenv("REVIEWFORGE_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    from reviewforge.config import load_config

    config = load_config()
    assert config.data_dir == tmp_path / "ReviewForgeData"
    assert config.data_dir_source == "default"
