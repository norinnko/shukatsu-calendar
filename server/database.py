import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

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
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            company TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT DEFAULT '',
            url TEXT DEFAULT '',
            memo TEXT DEFAULT '',
            status TEXT DEFAULT 'upcoming',
            notified_7d INTEGER DEFAULT 0,
            notified_0d INTEGER DEFAULT 0,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_event(user_id, event):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO events (
            id, user_id, company, type, title, date, time, url, memo,
            status, notified_7d, notified_0d, tags, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event["id"],
        user_id,
        event["company"],
        event["type"],
        event["title"],
        event["date"],
        event.get("time", ""),
        event.get("url", ""),
        event.get("memo", ""),
        event.get("status", "upcoming"),
        1 if event.get("notified_7d", False) else 0,
        1 if event.get("notified_0d", False) else 0,
        ",".join(event.get("tags", [])),
        event.get("created_at", datetime.now().isoformat()),
    ))

    conn.commit()
    conn.close()
    return True


def get_event_by_id(user_id, event_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM events
        WHERE user_id = ? AND id = ?
        LIMIT 1
    """, (user_id, event_id))

    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_events(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM events
        WHERE user_id = ?
        ORDER BY date ASC, time ASC, created_at ASC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_upcoming_events(user_id, days=30):
    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM events
        WHERE user_id = ?
          AND date >= ?
          AND date <= ?
        ORDER BY date ASC, time ASC, created_at ASC
    """, (user_id, today.isoformat(), end_date.isoformat()))

    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_events_by_month(user_id, year, month):
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        next_start = f"{year + 1:04d}-01-01"
    else:
        next_start = f"{year:04d}-{month + 1:02d}-01"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM events
        WHERE user_id = ?
          AND date >= ?
          AND date < ?
        ORDER BY date ASC, time ASC, created_at ASC
    """, (user_id, start, next_start))

    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_event(user_id, event_id, updates):
    allowed_fields = {
        "company", "title", "date", "time", "memo", "url",
        "type", "status", "notified_7d", "notified_0d"
    }

    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    if not filtered:
        return False, None

    set_clause = ", ".join([f"{key} = ?" for key in filtered.keys()])
    values = list(filtered.values()) + [user_id, event_id]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"UPDATE events SET {set_clause} WHERE user_id = ? AND id = ?",
        values
    )

    conn.commit()
    changed = cur.rowcount
    conn.close()

    if changed == 0:
        return False, None

    return True, get_event_by_id(user_id, event_id)


def delete_event(user_id, event_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM events
        WHERE user_id = ? AND id = ?
    """, (user_id, event_id))

    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0