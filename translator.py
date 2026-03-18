"""AI translation using the provider configured in transduck.yaml."""

import os

import anthropic
import openai

from config import TransduckUIConfig


class TranslatorError(Exception):
    pass


_SYSTEM_TEMPLATE = (
    "You are a professional translator. Translate the given text from {source_lang} "
    "to {target_lang}. Return ONLY the translated text, nothing else. "
    "Do NOT add quotation marks, brackets, or any wrapper characters that are not in the original. "
    "Preserve any placeholders like {{name}}, {{{{count}}}}, %s, ${{value}} exactly as they appear. "
    "Preserve brand names. Match the tone and formality of the original.\n\n"
    "Project context: {project_context}"
)

_USER_TEMPLATE = "Translate the following text:\n{source_text}\n\nString context: {string_context}"


def _build_messages(source_text: str, target_lang: str, string_context: str | None,
                    config: TransduckUIConfig) -> list[dict]:
    system_msg = _SYSTEM_TEMPLATE.format(
        source_lang=config.source_lang,
        target_lang=target_lang,
        project_context=config.project_context,
    )
    user_msg = _USER_TEMPLATE.format(
        source_text=source_text,
        string_context=string_context or "none",
    )
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def translate(source_text: str, target_lang: str, string_context: str | None,
              config: TransduckUIConfig) -> str:
    if not config.ai_translate_enabled:
        raise TranslatorError(
            "Claude Code provider is read-only and cannot be used "
            "for AI translation from the UI."
        )

    messages = _build_messages(source_text, target_lang, string_context, config)

    if config.provider == "openai":
        return _translate_openai(messages, config)
    elif config.provider == "claude_api":
        return _translate_claude(messages, config)
    else:
        raise TranslatorError(f"Unsupported provider: {config.provider}")


def _translate_openai(messages: list[dict], config: TransduckUIConfig) -> str:
    api_key = os.environ.get(config.api_key_env)
    client = openai.OpenAI(
        api_key=api_key,
        timeout=config.backend_timeout,
        max_retries=config.backend_max_retries,
    )
    response = client.chat.completions.create(
        model=config.backend_model,
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def _translate_claude(messages: list[dict], config: TransduckUIConfig) -> str:
    api_key = os.environ.get(config.api_key_env)
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=config.backend_model,
        max_tokens=1024,
        temperature=0.3,
        system=messages[0]["content"],
        messages=[{"role": "user", "content": messages[1]["content"]}],
    )
    return response.content[0].text.strip()
