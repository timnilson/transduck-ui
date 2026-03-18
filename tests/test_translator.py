import pytest
from unittest.mock import patch, MagicMock
from config import TransduckUIConfig
from pathlib import Path
from translator import translate, TranslatorError


def _make_config(provider="openai", model="gpt-4.1-mini"):
    return TransduckUIConfig(
        project_name="test",
        project_context="A test project",
        source_lang="EN",
        target_langs=["DE"],
        storage_path=Path("/tmp/test.lmdb"),
        provider=provider,
        api_key_env="OPENAI_API_KEY",
        token_env="CLAUDE_CODE_OAUTH_TOKEN",
        backend_model=model,
        backend_timeout=10,
        backend_max_retries=2,
        ai_translate_enabled=provider != "claude_code",
    )


def test_translate_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "  Hallo  "

    with patch("translator.openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        result = translate(
            source_text="Hello",
            target_lang="DE",
            string_context="greeting",
            config=_make_config(),
        )

    assert result == "Hallo"
    call_kwargs = mock_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs["messages"]
    assert "professional translator" in messages[0]["content"]
    assert "Hello" in messages[1]["content"]
    assert "greeting" in messages[1]["content"]


def test_translate_claude_api(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "  Hallo  "

    with patch("translator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        result = translate(
            source_text="Hello",
            target_lang="DE",
            string_context=None,
            config=_make_config(provider="claude_api", model="claude-sonnet-4-6"),
        )

    assert result == "Hallo"


def test_translate_claude_code_raises():
    cfg = _make_config(provider="claude_code")
    with pytest.raises(TranslatorError, match="read-only"):
        translate("Hello", "DE", None, cfg)
