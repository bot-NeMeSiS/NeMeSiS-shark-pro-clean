"""Authenticated support delivery to the existing application's admin inbox."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sqlite3

CATEGORIES = {'partidos', 'live', 'picks', 'telegram', 'cuenta', 'cancelacion', 'privacidad', 'general'}
PRIORITIES = {'normal', 'alta', 'baja'}


class SupportRejected(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def submit(db_path, *, user_id, request_id, subject, message, category, priority, now=None):
    if not user_id or not re.fullmatch(r'[0-9a-f]{32}', str(request_id or '')):
        raise SupportRejected('session')
    subject, message = str(subject or '').strip(), str(message or '').strip()
    if not 3 <= len(subject) <= 120 or not 10 <= len(message) <= 4000:
        raise SupportRejected('length')
    if category not in CATEGORIES or priority not in PRIORITIES:
        raise SupportRejected('category')
    # Reject explicit credential assignments; never log or echo their values.
    if re.search(r'(?i)\b(password|contrase[ñn]a|api[_ -]?key|secret|token)\s*[:=]\s*\S+', subject+' '+message):
        raise SupportRejected('sensitive')
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError('Support clock requires an absolute instant')
    instant = instant.astimezone(timezone.utc)
    conn = sqlite3.connect(str(db_path), timeout=8)
    try:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('''CREATE TABLE IF NOT EXISTS nemesis_support_requests (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, subject TEXT NOT NULL,
            message TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL)''')
        conn.execute('CREATE INDEX IF NOT EXISTS support_user_created ON nemesis_support_requests(user_id, created_at)')
        existing = conn.execute('SELECT user_id FROM nemesis_support_requests WHERE id=?', (request_id,)).fetchone()
        if existing:
            if existing[0] != str(user_id):
                raise SupportRejected('session')
            conn.commit()
            return request_id
        count, latest = conn.execute('SELECT COUNT(*), MAX(created_at) FROM nemesis_support_requests WHERE user_id=? AND created_at>=?',
                                     (str(user_id), (instant-timedelta(hours=1)).isoformat())).fetchone()
        if count >= 3 or (latest and datetime.fromisoformat(latest) > instant-timedelta(seconds=60)):
            raise SupportRejected('rate')
        conn.execute('INSERT INTO nemesis_support_requests(id,user_id,subject,message,category,priority,created_at) VALUES(?,?,?,?,?,?,?)',
                     (request_id,str(user_id),subject,message,category,priority,instant.isoformat()))
        conn.commit()
        return request_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def admin_snapshot(db_path):
    """No schema creation or storage mutation when an admin reads the inbox."""
    uri = Path(db_path).resolve().as_uri()+'?mode=ro'
    conn = sqlite3.connect(uri, uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='nemesis_support_requests'").fetchone():
            return {'total': 0, 'open': 0, 'recent': []}
        counts = conn.execute("SELECT COUNT(*) AS total, COALESCE(SUM(status='open'),0) AS open FROM nemesis_support_requests").fetchone()
        rows = conn.execute('SELECT id,subject,message,category,priority,status,created_at FROM nemesis_support_requests ORDER BY created_at DESC LIMIT 40').fetchall()
        return {**dict(counts), 'recent':[dict(row) for row in rows]}
    finally:
        conn.close()
