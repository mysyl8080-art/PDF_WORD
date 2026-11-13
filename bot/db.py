"""Tiny SQLite store: user language + usage statistics."""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .config import settings


class DB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users(
                    user_id INTEGER PRIMARY KEY, lang TEXT, first_seen INTEGER, last_seen INTEGER);
                CREATE TABLE IF NOT EXISTS usage(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tool TEXT,
                    ok INTEGER, ts INTEGER, seconds REAL);
                CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage(ts);
                """
            )

    def touch_user(self, user_id: int, default_lang: str) -> str:
        now = int(time.time())
        with self._lock:
            row = self._conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
            if row:
                self._conn.execute("UPDATE users SET last_seen=? WHERE user_id=?", (now, user_id))
                self._conn.commit()
                return row[0]
            self._conn.execute("INSERT INTO users VALUES(?,?,?,?)", (user_id, default_lang, now, now))
            self._conn.commit()
            return default_lang

    def set_lang(self, user_id: int, lang: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
            self._conn.commit()

    def log_usage(self, user_id: int, tool: str, ok: bool, seconds: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO usage(user_id,tool,ok,ts,seconds) VALUES(?,?,?,?,?)",
                (user_id, tool, int(ok), int(time.time()), seconds),
            )
            self._conn.commit()

    def stats(self) -> dict:
        day = int(time.time()) - 86400
        with self._lock:
            c = self._conn
            users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active = c.execute("SELECT COUNT(*) FROM users WHERE last_seen>?", (day,)).fetchone()[0]
            jobs = c.execute("SELECT COUNT(*), COALESCE(SUM(ok),0) FROM usage").fetchone()
            jobs24 = c.execute("SELECT COUNT(*) FROM usage WHERE ts>?", (day,)).fetchone()[0]
            top = c.execute(
                "SELECT tool, COUNT(*) n FROM usage GROUP BY tool ORDER BY n DESC LIMIT 8"
            ).fetchall()
        return {"users": users, "active24": active, "jobs": jobs[0], "ok": jobs[1], "jobs24": jobs24, "top": top}


db = DB(settings.db_path)