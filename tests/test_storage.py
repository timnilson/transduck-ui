import sqlite3
import pytest
from storage import TranslationStore


def _make_db(tmp_path, entries):
    """Create a SQLite DB with translation entries. Each entry is (key_str, value_dict)."""
    db_path = tmp_path / "translations.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE translations (
            source_lang TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            plural_category TEXT NOT NULL DEFAULT '',
            source_text TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            project_context_hash TEXT NOT NULL,
            string_context_hash TEXT NOT NULL,
            string_context TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (source_lang, target_lang, content_hash, plural_category)
        )
    """)
    for key_str, value_dict in entries:
        parts = key_str.split("|")
        conn.execute(
            """INSERT INTO translations
               (source_lang, target_lang, content_hash, plural_category,
                source_text, translated_text, model, status, created_at,
                project_context_hash, string_context_hash, string_context)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else "",
             value_dict["source_text"], value_dict["translated_text"],
             value_dict["model"], value_dict["status"], value_dict["created_at"],
             value_dict["project_context_hash"], value_dict["string_context_hash"],
             value_dict.get("string_context", "")),
        )
    conn.commit()
    conn.close()
    return db_path


def _entry(source_text="Hello", translated_text="Hallo", model="gpt-4.1-mini",
           status="translated", string_context=""):
    return {
        "source_text": source_text,
        "translated_text": translated_text,
        "model": model,
        "status": status,
        "created_at": "2026-03-18T00:00:00+00:00",
        "project_context_hash": "abc123",
        "string_context_hash": "def456",
        "string_context": string_context,
    }


@pytest.fixture
def store(tmp_path):
    db_path = _make_db(tmp_path, [
        ("EN|DE|hash1|", _entry("Hello", "Hallo")),
        ("EN|DE|hash2|", _entry("Goodbye", "Tschuess", status="failed")),
        ("EN|ES|hash1|", _entry("Hello", "Hola")),
        ("EN|DE|hash3|", _entry("Book", "Buchen", string_context="Hotel booking")),
    ])
    s = TranslationStore(db_path, "EN")
    yield s
    s.close()


def test_get_all_filters_by_language(store):
    results = store.get_all("DE")
    assert len(results) == 3
    source_texts = {r["source_text"] for r in results}
    assert source_texts == {"Hello", "Goodbye", "Book"}


def test_get_all_search_source_text(store):
    results = store.get_all("DE", query="hello")
    assert len(results) == 1
    assert results[0]["source_text"] == "Hello"


def test_get_all_search_translated_text(store):
    results = store.get_all("DE", query="buchen")
    assert len(results) == 1
    assert results[0]["source_text"] == "Book"


def test_get_all_includes_key_and_context(store):
    results = store.get_all("DE", query="book")
    assert len(results) == 1
    assert results[0]["key"] == "EN|DE|hash3|"
    assert results[0]["string_context"] == "Hotel booking"


def test_get_stats(store):
    stats = store.get_stats()
    assert stats["DE"]["translated"] == 2
    assert stats["DE"]["failed"] == 1
    assert stats["ES"]["translated"] == 1
    assert stats["ES"]["failed"] == 0


def test_get_entry(store):
    entry = store.get_entry("EN|DE|hash1|")
    assert entry["source_text"] == "Hello"
    assert entry["translated_text"] == "Hallo"


def test_get_entry_missing(store):
    entry = store.get_entry("EN|DE|nonexistent|")
    assert entry is None


def test_update_entry(store):
    store.update_entry("EN|DE|hash1|", "Hallo Welt", "human")
    entry = store.get_entry("EN|DE|hash1|")
    assert entry["translated_text"] == "Hallo Welt"
    assert entry["model"] == "human"
    assert entry["status"] == "translated"
    assert entry["source_text"] == "Hello"
    assert entry["project_context_hash"] == "abc123"


def test_update_entry_updates_created_at(store):
    old = store.get_entry("EN|DE|hash1|")
    store.update_entry("EN|DE|hash1|", "Hallo Welt", "human")
    new = store.get_entry("EN|DE|hash1|")
    assert new["created_at"] != old["created_at"]


def test_get_all_with_plural_entries(tmp_path):
    db_path = _make_db(tmp_path, [
        ("EN|DE|hash1|one", _entry("{count} item", "{count} Artikel")),
        ("EN|DE|hash1|other", _entry("{count} items", "{count} Artikel")),
    ])
    store = TranslationStore(db_path, "EN")
    results = store.get_all("DE")
    assert len(results) == 2
    categories = {r["plural_category"] for r in results}
    assert categories == {"one", "other"}
    store.close()
