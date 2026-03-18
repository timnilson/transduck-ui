"""Flask app for transduck-ui."""

import sys
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from config import load_config, ConfigError
from storage import TranslationStore
from translator import translate, TranslatorError

app = Flask(__name__)

_app_dir = Path(__file__).parent
_yaml_path = _app_dir.parent / "transduck.yaml"

try:
    config = load_config(_yaml_path)
except ConfigError as e:
    print(f"Error: {e}", file=sys.stderr)
    print("Make sure transduck-ui is cloned inside your project directory", file=sys.stderr)
    print("and that you have run 'transduck init' in the project root.", file=sys.stderr)
    sys.exit(1)

store = TranslationStore(config.storage_path, config.source_lang)


@app.context_processor
def inject_globals():
    return {
        "project_name": config.project_name,
        "source_lang": config.source_lang,
        "target_langs": config.target_langs,
        "ai_translate_enabled": config.ai_translate_enabled,
    }


@app.route("/")
def index():
    stats = store.get_stats()
    languages = []
    for lang in config.target_langs:
        lang_stats = stats.get(lang, {"translated": 0, "failed": 0})
        languages.append({
            "code": lang,
            "translated": lang_stats["translated"],
            "failed": lang_stats["failed"],
            "total": lang_stats["translated"] + lang_stats["failed"],
        })
    return render_template("index.html", languages=languages)


@app.route("/translations/<lang>")
def translations(lang):
    lang = lang.upper()
    query = request.args.get("q", "").strip()
    entries = store.get_all(lang, query=query or None)
    return render_template("translations.html", lang=lang, entries=entries, query=query)


@app.route("/api/edit", methods=["POST"])
def api_edit():
    data = request.get_json()
    key = data.get("key")
    translated_text = data.get("translated_text", "").strip()
    if not key or not translated_text:
        return jsonify({"ok": False, "error": "Missing key or translated_text"}), 400
    try:
        entry = store.update_entry(key, translated_text, "human")
        return jsonify({"ok": True, "translated_text": entry["translated_text"]})
    except KeyError:
        return jsonify({"ok": False, "error": "Entry not found"}), 404


@app.route("/api/ai-translate", methods=["POST"])
def api_ai_translate():
    data = request.get_json()
    key = data.get("key")
    if not key:
        return jsonify({"ok": False, "error": "Missing key"}), 400

    entry = store.get_entry(key)
    if entry is None:
        return jsonify({"ok": False, "error": "Entry not found"}), 404

    target_lang = key.split("|")[1]

    try:
        translated = translate(
            source_text=entry["source_text"],
            target_lang=target_lang,
            string_context=entry.get("string_context") or None,
            config=config,
        )
    except TranslatorError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"Translation failed: {e}"}), 500

    updated = store.update_entry(key, translated, config.backend_model)
    return jsonify({
        "ok": True,
        "translated_text": updated["translated_text"],
        "model": updated["model"],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5555)
