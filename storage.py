"""LMDB translation storage for transduck-ui."""

import json
from datetime import datetime, timezone
from pathlib import Path

import lmdb

MAP_SIZE = 1024 * 1024 * 1024  # 1 GB


def _parse_key(key_bytes: bytes) -> dict:
    parts = key_bytes.decode().split("|")
    return {
        "source_lang": parts[0],
        "target_lang": parts[1],
        "content_hash": parts[2],
        "plural_category": parts[3] if len(parts) > 3 else "",
    }


class TranslationStore:
    def __init__(self, db_path: Path, source_lang: str):
        self._env = lmdb.open(str(db_path), map_size=MAP_SIZE, subdir=True, readonly=False)
        self._source_lang = source_lang

    def get_all(self, target_lang: str, query: str | None = None) -> list[dict]:
        prefix = f"{self._source_lang}|{target_lang}|".encode()
        query_lower = query.lower() if query else None
        results = []

        with self._env.begin() as txn:
            cursor = txn.cursor()
            for key_bytes, value_bytes in cursor:
                if not key_bytes.startswith(prefix):
                    continue
                parsed_key = _parse_key(key_bytes)
                entry = json.loads(value_bytes)

                if query_lower:
                    source_match = query_lower in entry.get("source_text", "").lower()
                    trans_match = query_lower in entry.get("translated_text", "").lower()
                    if not source_match and not trans_match:
                        continue

                results.append({
                    "key": key_bytes.decode(),
                    "source_text": entry["source_text"],
                    "translated_text": entry["translated_text"],
                    "string_context": entry.get("string_context", ""),
                    "status": entry["status"],
                    "model": entry["model"],
                    "created_at": entry["created_at"],
                    "plural_category": parsed_key["plural_category"],
                })

        return results

    def get_stats(self) -> dict:
        stats: dict[str, dict[str, int]] = {}

        with self._env.begin() as txn:
            cursor = txn.cursor()
            for key_bytes, value_bytes in cursor:
                parsed_key = _parse_key(key_bytes)
                lang = parsed_key["target_lang"]
                entry = json.loads(value_bytes)

                if lang not in stats:
                    stats[lang] = {"translated": 0, "failed": 0}

                if entry["status"] == "translated":
                    stats[lang]["translated"] += 1
                elif entry["status"] == "failed":
                    stats[lang]["failed"] += 1

        return stats

    def get_entry(self, key: str) -> dict | None:
        with self._env.begin() as txn:
            raw = txn.get(key.encode())
            if raw is None:
                return None
            return json.loads(raw)

    def update_entry(self, key: str, translated_text: str, model: str) -> dict:
        key_bytes = key.encode()

        with self._env.begin(write=True) as txn:
            raw = txn.get(key_bytes)
            if raw is None:
                raise KeyError(f"Entry not found: {key}")

            entry = json.loads(raw)
            entry["translated_text"] = translated_text
            entry["model"] = model
            entry["status"] = "translated"
            entry["created_at"] = datetime.now(timezone.utc).isoformat()

            txn.put(key_bytes, json.dumps(entry).encode(), overwrite=True)

        return entry

    def close(self):
        self._env.close()
