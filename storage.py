"""SQLite translation storage for transduck-ui."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class TranslationStore:
    def __init__(self, db_path: Path, source_lang: str):
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._source_lang = source_lang

    def get_all(self, target_lang: str, query: str | None = None) -> list[dict]:
        sql = """SELECT source_lang, target_lang, content_hash, plural_category,
                        source_text, translated_text, string_context, status, model, created_at
                 FROM translations
                 WHERE source_lang = ? AND target_lang = ?"""
        params: list = [self._source_lang, target_lang]

        if query:
            sql += " AND (source_text LIKE ? OR translated_text LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like])

        rows = self._conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            key = f"{row['source_lang']}|{row['target_lang']}|{row['content_hash']}|{row['plural_category']}"
            results.append({
                "key": key,
                "source_text": row["source_text"],
                "translated_text": row["translated_text"],
                "string_context": row["string_context"] or "",
                "status": row["status"],
                "model": row["model"],
                "created_at": row["created_at"],
                "plural_category": row["plural_category"],
            })
        return results

    def get_stats(self) -> dict:
        rows = self._conn.execute(
            "SELECT target_lang, status, COUNT(*) as count FROM translations GROUP BY target_lang, status"
        ).fetchall()
        stats: dict[str, dict[str, int]] = {}
        for row in rows:
            lang = row["target_lang"]
            if lang not in stats:
                stats[lang] = {"translated": 0, "failed": 0}
            if row["status"] == "translated":
                stats[lang]["translated"] += row["count"]
            elif row["status"] == "failed":
                stats[lang]["failed"] += row["count"]
        return stats

    def get_entry(self, key: str) -> dict | None:
        parts = key.split("|")
        row = self._conn.execute(
            "SELECT * FROM translations WHERE source_lang=? AND target_lang=? AND content_hash=? AND plural_category=?",
            (parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else ""),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def update_entry(self, key: str, translated_text: str, model: str) -> dict:
        parts = key.split("|")
        source_lang, target_lang, content_hash = parts[0], parts[1], parts[2]
        plural_category = parts[3] if len(parts) > 3 else ""

        row = self._conn.execute(
            "SELECT * FROM translations WHERE source_lang=? AND target_lang=? AND content_hash=? AND plural_category=?",
            (source_lang, target_lang, content_hash, plural_category),
        ).fetchone()
        if row is None:
            raise KeyError(f"Entry not found: {key}")

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """UPDATE translations SET translated_text=?, model=?, status='translated', created_at=?
               WHERE source_lang=? AND target_lang=? AND content_hash=? AND plural_category=?""",
            (translated_text, model, now, source_lang, target_lang, content_hash, plural_category),
        )
        self._conn.commit()

        entry = dict(row)
        entry["translated_text"] = translated_text
        entry["model"] = model
        entry["status"] = "translated"
        entry["created_at"] = now
        return entry

    def close(self):
        self._conn.close()
