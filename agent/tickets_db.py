import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("tickets.db")
STATUSES = ["Open", "In progress", "Needs info", "Resolved"]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            priority TEXT,
            category TEXT,
            assignment_group TEXT,
            status TEXT NOT NULL DEFAULT 'Open',
            affected_users TEXT,
            reported_by TEXT,
            what_happened TEXT,
            likely_cause TEXT,
            recommended_fix TEXT,
            checks_run TEXT,
            incident TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    return conn


def ticket_code(number):
    return f"OC-{number:04d}"


def save_ticket(t):
    """Save a reviewed ticket. Returns its code, e.g. OC-0001."""
    now = datetime.now().isoformat(timespec="seconds")
    conn = _connect()
    with conn:
        cur = conn.execute(
            """INSERT INTO tickets (title, priority, category, assignment_group, status,
                   affected_users, reported_by, what_happened, likely_cause,
                   recommended_fix, checks_run, incident, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (t["title"], t["priority"], t["category"], t["assignment_group"],
             t["affected_users"], t["reported_by"], t["what_happened"],
             t["likely_cause"], t["recommended_fix"], json.dumps(t["checks_run"]),
             t["incident"], now, now),
        )
    conn.close()
    return ticket_code(cur.lastrowid)


def list_tickets():
    """All tickets, newest first."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
    conn.close()
    tickets = []
    for r in rows:
        t = dict(r)
        t["code"] = ticket_code(t["id"])
        t["checks_run"] = json.loads(t["checks_run"] or "[]")
        tickets.append(t)
    return tickets


def update_status(ticket_id, status):
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status}")
    conn = _connect()
    with conn:
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(timespec="seconds"), ticket_id),
        )
    conn.close()