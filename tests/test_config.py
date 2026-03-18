import pytest
from pathlib import Path
from config import load_config, ConfigError


@pytest.fixture
def config_dir(tmp_path):
    yaml_content = """\
project:
  name: test-project
  context: "A test project"

languages:
  source: EN
  targets:
    - DE
    - ES

storage:
  path: ./translations.lmdb

backend:
  provider: openai
  api_key_env: OPENAI_API_KEY
  model: gpt-4.1-mini
  timeout_seconds: 10
  max_retries: 2
"""
    (tmp_path / "transduck.yaml").write_text(yaml_content)
    return tmp_path


def test_load_config(config_dir):
    cfg = load_config(config_dir / "transduck.yaml")
    assert cfg.project_name == "test-project"
    assert cfg.project_context == "A test project"
    assert cfg.source_lang == "EN"
    assert cfg.target_langs == ["DE", "ES"]
    assert cfg.storage_path == config_dir / "translations.lmdb"
    assert cfg.provider == "openai"
    assert cfg.api_key_env == "OPENAI_API_KEY"
    assert cfg.backend_model == "gpt-4.1-mini"


def test_load_config_defaults(tmp_path):
    yaml_content = """\
project:
  name: minimal
  context: ""

languages:
  source: EN
  targets: [DE]

storage:
  path: ./translations.lmdb

backend: {}
"""
    (tmp_path / "transduck.yaml").write_text(yaml_content)
    cfg = load_config(tmp_path / "transduck.yaml")
    assert cfg.provider == "openai"
    assert cfg.api_key_env == "OPENAI_API_KEY"
    assert cfg.backend_model == "gpt-4.1-mini"
    assert cfg.backend_timeout == 10
    assert cfg.backend_max_retries == 2


def test_load_config_claude_code_marks_read_only(tmp_path):
    yaml_content = """\
project:
  name: test
  context: ""

languages:
  source: EN
  targets: [DE]

storage:
  path: ./translations.lmdb

backend:
  provider: claude_code
"""
    (tmp_path / "transduck.yaml").write_text(yaml_content)
    cfg = load_config(tmp_path / "transduck.yaml")
    assert cfg.provider == "claude_code"
    assert cfg.ai_translate_enabled is False


def test_load_config_missing_file():
    with pytest.raises(ConfigError, match="not found"):
        load_config(Path("/nonexistent/transduck.yaml"))


def test_load_config_missing_required_fields(tmp_path):
    (tmp_path / "transduck.yaml").write_text("project: {}")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "transduck.yaml")


def test_storage_path_resolved_relative_to_yaml(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    yaml_content = """\
project:
  name: test
  context: ""

languages:
  source: EN
  targets: [DE]

storage:
  path: ./data/translations.lmdb

backend: {}
"""
    (sub / "transduck.yaml").write_text(yaml_content)
    cfg = load_config(sub / "transduck.yaml")
    assert cfg.storage_path == (sub / "data" / "translations.lmdb").resolve()
