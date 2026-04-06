import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "events.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def add_event(user_id, company, title, event_date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO events (user_id, company, title, event_date)
        VALUES (?, ?, ?, ?)
    """, (user_id, company, title, event_date))

    conn.commit()
    conn.close()


def get_upcoming_events(user_id, limit=10):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, company, title, event_date
        FROM events
        WHERE user_id = ?
        ORDER BY event_date ASC
        LIMIT ?
    """, (user_id, limit))

    rows = cur.fetchall()
    conn.close()
    return rows