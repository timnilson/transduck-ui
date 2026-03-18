"""Parse transduck.yaml and expose config."""

from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class TransduckUIConfig:
    project_name: str
    project_context: str
    source_lang: str
    target_langs: list[str]
    storage_path: Path
    provider: str
    api_key_env: str
    token_env: str
    backend_model: str
    backend_timeout: int
    backend_max_retries: int
    ai_translate_enabled: bool


def load_config(yaml_path: Path) -> TransduckUIConfig:
    yaml_path = Path(yaml_path)
    if not yaml_path.is_file():
        raise ConfigError(f"Config file not found: {yaml_path}")

    with open(yaml_path) as f:
        raw = yaml.safe_load(f)

    try:
        project = raw["project"]
        project_name = project["name"]
        project_context = project.get("context", "")
        languages = raw["languages"]
        source_lang = languages["source"].upper()
        target_langs = [lang.upper() for lang in languages["targets"]]
    except (KeyError, TypeError) as e:
        raise ConfigError(f"Missing required config field: {e}")

    config_dir = yaml_path.parent
    storage_rel = raw.get("storage", {}).get("path", "./translations.lmdb")
    storage_path = (config_dir / storage_rel).resolve()

    backend = raw.get("backend", {})
    provider = backend.get("provider", "openai")
    api_key_env = backend.get("api_key_env", "OPENAI_API_KEY")
    token_env = backend.get("token_env", "CLAUDE_CODE_OAUTH_TOKEN")
    backend_model = backend.get("model", "gpt-4.1-mini")
    backend_timeout = backend.get("timeout_seconds", 10)
    backend_max_retries = backend.get("max_retries", 2)

    ai_translate_enabled = provider != "claude_code"

    env_file = config_dir / ".env"
    if env_file.is_file():
        load_dotenv(env_file)

    return TransduckUIConfig(
        project_name=project_name,
        project_context=project_context,
        source_lang=source_lang,
        target_langs=target_langs,
        storage_path=storage_path,
        provider=provider,
        api_key_env=api_key_env,
        token_env=token_env,
        backend_model=backend_model,
        backend_timeout=backend_timeout,
        backend_max_retries=backend_max_retries,
        ai_translate_enabled=ai_translate_enabled,
    )
