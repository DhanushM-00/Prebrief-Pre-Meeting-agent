"""Tiny SQLite TTL cache for upstream search responses (saves credits, steadies demos)."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any


class SearchCache:
    def __init__(self, path: str, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS search_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, fetched_at REAL NOT NULL)"
        )
        self._db.commit()

    def get(self, key: str) -> Any | None:
        with self._lock:
            row = self._db.execute("SELECT value, fetched_at FROM search_cache WHERE key=?", (key,)).fetchone()
        if not row or time.time() - row[1] > self._ttl:
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO search_cache (key, value, fetched_at) VALUES (?,?,?)",
                (key, json.dumps(value), time.time()),
            )
            self._db.commit()
