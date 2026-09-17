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
