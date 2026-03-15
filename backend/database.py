import sqlite3
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id        INTEGER NOT NULL,
            sender_username  TEXT NOT NULL,
            room             TEXT NOT NULL,
            content          TEXT NOT NULL,
            is_filtered      INTEGER DEFAULT 0,
            original_content TEXT,
            toxicity_score   REAL DEFAULT 0.0,
            toxic_words      TEXT,
            suggestion       TEXT,
            timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS filter_logs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            username         TEXT NOT NULL,
            original_message TEXT NOT NULL,
            cleaned_message  TEXT,
            toxicity_score   REAL,
            toxic_words      TEXT,
            suggestion       TEXT,
            action           TEXT,
            timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    # Add admin / ban flags if they don't exist yet
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    cursor.execute("INSERT OR IGNORE INTO rooms (name) VALUES ('General')")
    cursor.execute("INSERT OR IGNORE INTO rooms (name) VALUES ('Support')")
    cursor.execute("INSERT OR IGNORE INTO rooms (name) VALUES ('Random')")
    conn.commit()
    conn.close()
    print("[DB] Database initialized.")

# ── User helpers ──────────────────────────────────────────────────────────────

def create_user(username, password):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "Username already taken."
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    if row:
        return True, dict(row)
    return False, None

def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def ensure_default_admin():
    """
    Ensure there is at least one admin user.
    Creates a default 'admin' account with password 'admin123' if none exists.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin=1")
    has_admin = cur.fetchone()[0] > 0
    if not has_admin:
        # Try to create admin user if username is free
        cur.execute("SELECT id FROM users WHERE username='admin'")
        existing = cur.fetchone()
        if existing:
            cur.execute("UPDATE users SET is_admin=1 WHERE id=?", (existing[0],))
        else:
            cur.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                ("admin", hash_password("admin123")),
            )
    conn.commit()
    conn.close()


def set_user_banned(user_id, banned: bool):
    conn = get_db()
    conn.execute(
        "UPDATE users SET is_banned=? WHERE id=?",
        (1 if banned else 0, user_id),
    )
    conn.commit()
    conn.close()


def set_user_password(user_id: int, new_password: str):
    """Directly set a new password hash for a user (admin use)."""
    conn = get_db()
    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(new_password), user_id),
    )
    conn.commit()
    conn.close()


def get_user_toxicity_overview():
    """
    Return per-user toxicity summary: counts and total score.
    """
    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            u.id,
            u.username,
            COALESCE(u.is_admin, 0) AS is_admin,
            COALESCE(u.is_banned, 0) AS is_banned,
            COUNT(fl.id) AS incidents,
            COALESCE(SUM(fl.toxicity_score), 0.0) AS total_toxicity
        FROM users u
        LEFT JOIN filter_logs fl ON fl.user_id = u.id
        GROUP BY u.id, u.username, u.is_admin, u.is_banned
        ORDER BY incidents DESC, total_toxicity DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Message helpers ───────────────────────────────────────────────────────────

def save_message(sender_id, sender_username, room, content,
                 is_filtered=False, original_content=None,
                 toxicity_score=0.0, toxic_words=None, suggestion=None):
    conn = get_db()
    conn.execute(
        """INSERT INTO messages
           (sender_id, sender_username, room, content, is_filtered,
            original_content, toxicity_score, toxic_words, suggestion)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (sender_id, sender_username, room, content,
         1 if is_filtered else 0,
         original_content,
         toxicity_score,
         ','.join(toxic_words) if toxic_words else None,
         suggestion)
    )
    conn.commit()
    conn.close()

def get_room_messages(room, limit=50):
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM messages WHERE room=?
           ORDER BY timestamp DESC LIMIT ?""",
        (room, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_recent_messages(limit=200):
    """Return most recent messages across all rooms (for admin)."""
    conn = get_db()
    rows = conn.execute(
        """SELECT id, sender_username, room, content, is_filtered,
                  toxicity_score, timestamp
           FROM messages
           ORDER BY timestamp DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_message(message_id: int):
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id=?", (message_id,))
    conn.commit()
    conn.close()


def clear_all_messages(include_logs: bool = True):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages")
    if include_logs:
        cur.execute("DELETE FROM filter_logs")
    conn.commit()
    conn.close()

# ── Filter log helpers ────────────────────────────────────────────────────────

def log_filter_event(user_id, username, original_message,
                     cleaned_message, toxicity_score,
                     toxic_words, suggestion, action):
    conn = get_db()
    conn.execute(
        """INSERT INTO filter_logs
           (user_id, username, original_message, cleaned_message,
            toxicity_score, toxic_words, suggestion, action)
           VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, username, original_message, cleaned_message,
         toxicity_score,
         ','.join(toxic_words) if toxic_words else '',
         suggestion, action)
    )
    conn.commit()
    conn.close()

def get_filter_logs(limit=200):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM filter_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_filter_logs(user_id, limit=100):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM filter_logs WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard_stats():
    conn = get_db()
    total_messages   = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    filtered_count   = conn.execute("SELECT COUNT(*) FROM messages WHERE is_filtered=1").fetchone()[0]
    total_users      = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    blocked_count    = conn.execute("SELECT COUNT(*) FROM filter_logs WHERE action='blocked'").fetchone()[0]
    warned_count     = conn.execute("SELECT COUNT(*) FROM filter_logs WHERE action='warned'").fetchone()[0]
    top_offenders    = conn.execute(
        """SELECT username, COUNT(*) as cnt FROM filter_logs
           GROUP BY username ORDER BY cnt DESC LIMIT 5"""
    ).fetchall()
    conn.close()
    return {
        "total_messages": total_messages,
        "filtered_count": filtered_count,
        "total_users": total_users,
        "blocked_count": blocked_count,
        "warned_count": warned_count,
        "top_offenders": [dict(r) for r in top_offenders],
        "filter_rate": round((filtered_count / total_messages * 100) if total_messages else 0, 1)
    }
