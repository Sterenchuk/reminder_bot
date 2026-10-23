import os
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id   INTEGER NOT NULL,
    text      TEXT    NOT NULL,
    kind      TEXT    NOT NULL CHECK (kind IN ('once', 'daily', 'weekdays')),
    at_time   TEXT    NOT NULL,   -- local wall-clock time, "HH:MM"
    next_run  TEXT    NOT NULL    -- UTC, "YYYY-MM-DDTHH:MM:SSZ"
);
CREATE INDEX IF NOT EXISTS idx_reminders_next_run ON reminders(next_run);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def connect(path: str):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: str) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def add_reminder(path, chat_id, text, kind, at_time, next_run) -> int:
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO reminders (chat_id, text, kind, at_time, next_run) VALUES (?, ?, ?, ?, ?)",
            (chat_id, text, kind, at_time, next_run),
        )
        return cur.lastrowid


def list_reminders(path, chat_id):
    with connect(path) as conn:
        return conn.execute(
            "SELECT * FROM reminders WHERE chat_id = ? ORDER BY next_run", (chat_id,)
        ).fetchall()


def delete_reminder(path, chat_id, reminder_id) -> bool:
    with connect(path) as conn:
        cur = conn.execute(
            "DELETE FROM reminders WHERE id = ? AND chat_id = ?", (reminder_id, chat_id)
        )
        return cur.rowcount > 0


def due_reminders(path, now_iso):
    with connect(path) as conn:
        return conn.execute(
            "SELECT * FROM reminders WHERE next_run <= ? ORDER BY next_run", (now_iso,)
        ).fetchall()


def set_next_run(path, reminder_id, next_run) -> None:
    with connect(path) as conn:
        conn.execute("UPDATE reminders SET next_run = ? WHERE id = ?", (next_run, reminder_id))


def snooze_reminder(path, chat_id, reminder_id, next_run) -> bool:
    """Move one of this chat's reminders to a later run time."""
    with connect(path) as conn:
        cur = conn.execute(
            "UPDATE reminders SET next_run = ? WHERE id = ? AND chat_id = ?",
            (next_run, reminder_id, chat_id),
        )
        return cur.rowcount > 0


def delete_by_id(path, reminder_id) -> None:
    with connect(path) as conn:
        conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))


def count_reminders(path) -> int:
    with connect(path) as conn:
        return conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]


def get_meta(path, key):
    with connect(path) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_meta(path, key, value) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
