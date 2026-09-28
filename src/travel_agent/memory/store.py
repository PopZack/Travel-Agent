"""记忆存储：SQLite 存用户偏好与历史行程。

MVP 用同步 sqlite3；后续可换 aiosqlite。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

_DB_PATH = Path("travel_agent_memory.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB_PATH)
    c.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id TEXT PRIMARY KEY,
            prefs_json TEXT,
            updated_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            query TEXT,
            itinerary_json TEXT,
            created_at TEXT
        )
    """)
    return c


def save_preferences(user_id: str, prefs: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO preferences VALUES (?, ?, ?)",
            (user_id, json.dumps(prefs, ensure_ascii=False), datetime.now().isoformat()),
        )


def load_preferences(user_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT prefs_json FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None


def save_trip(user_id: str, query: str, itinerary: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO trips (user_id, query, itinerary_json, created_at) VALUES (?, ?, ?, ?)",
            (user_id, query, json.dumps(itinerary, ensure_ascii=False), datetime.now().isoformat()),
        )


def list_trips(user_id: str, limit: int = 10) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, query, created_at FROM trips WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [{"id": r[0], "query": r[1], "created_at": r[2]} for r in rows]
