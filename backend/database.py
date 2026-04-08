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
            is_private  INTEGER DEFAULT 0,
            owner_id    INTEGER,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS room_members (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id     INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(room_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS room_invitations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id     INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            inviter_id  INTEGER NOT NULL,
            status      TEXT DEFAULT 'pending',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (inviter_id) REFERENCES users(id),
            UNIQUE(room_id, user_id)
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

        CREATE TABLE IF NOT EXISTS friendships (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            friend_id        INTEGER NOT NULL,
            status           TEXT DEFAULT 'pending',
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (friend_id) REFERENCES users(id),
            UNIQUE(user_id, friend_id)
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
    
    # Add private room columns to rooms table
    try:
        cursor.execute("ALTER TABLE rooms ADD COLUMN is_private INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE rooms ADD COLUMN owner_id INTEGER")
    except sqlite3.OperationalError:
        pass
    
    # Create room_members table if it doesn't exist
    try:
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS room_members (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(room_id, user_id)
            );
        ''')
    except sqlite3.OperationalError:
        pass
    
    # Create room_invitations table if it doesn't exist
    try:
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS room_invitations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                inviter_id  INTEGER NOT NULL,
                status      TEXT DEFAULT 'pending',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (inviter_id) REFERENCES users(id),
                UNIQUE(room_id, user_id)
            );
        ''')
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


def delete_user(user_id: int):
    """Delete a user and all associated data (messages, logs, friendships)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # Delete user's messages
        cursor.execute("DELETE FROM messages WHERE sender_id=?", (user_id,))
        
        # Delete user's filter logs
        cursor.execute("DELETE FROM filter_logs WHERE user_id=?", (user_id,))
        
        # Delete user's friendships (both directions)
        cursor.execute("DELETE FROM friendships WHERE user_id=? OR friend_id=?", (user_id, user_id))
        
        # Delete user from room members
        cursor.execute("DELETE FROM room_members WHERE user_id=?", (user_id,))
        
        # Delete room invitations sent by user
        cursor.execute("DELETE FROM room_invitations WHERE user_id=? OR inviter_id=?", (user_id, user_id))
        
        # Delete private rooms owned by user
        rooms_to_delete = cursor.execute("SELECT id FROM rooms WHERE owner_id=?", (user_id,)).fetchall()
        for room in rooms_to_delete:
            cursor.execute("DELETE FROM room_members WHERE room_id=?", (room[0],))
            cursor.execute("DELETE FROM room_invitations WHERE room_id=?", (room[0],))
            cursor.execute("DELETE FROM messages WHERE room=?", (room[0],))
        cursor.execute("DELETE FROM rooms WHERE owner_id=?", (user_id,))
        
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        
        conn.commit()
        conn.close()
        return True, "User deleted successfully."
    except Exception as e:
        conn.close()
        return False, f"Error deleting user: {str(e)}"


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

# ---- Friend Management Functions ----

def send_friend_request(user_id, friend_username):
    """Send a friend request to another user."""
    conn = get_db()
    try:
        # Find the target user
        friend = conn.execute("SELECT id FROM users WHERE username=?", (friend_username,)).fetchone()
        if not friend:
            conn.close()
            return False, "User not found.", None
        
        friend_id = friend[0]
        
        # Can't add yourself
        if user_id == friend_id:
            conn.close()
            return False, "Cannot add yourself as a friend.", None
        
        # Check if friendship already exists
        existing = conn.execute(
            "SELECT id, status FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
            (user_id, friend_id, friend_id, user_id)
        ).fetchone()
        
        if existing:
            if existing[1] == 'accepted':
                conn.close()
                return False, "Already friends.", None
            elif existing[1] == 'pending':
                conn.close()
                return False, "Friend request already sent.", None
        
        # Create friend request
        conn.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (?, ?, 'pending')",
            (user_id, friend_id)
        )
        conn.commit()
        conn.close()
        return True, "Friend request sent.", friend_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Friend request already exists.", None

def accept_friend_request(user_id, requester_id):
    """Accept a friend request."""
    conn = get_db()
    try:
        # Update the existing request to accepted
        conn.execute(
            "UPDATE friendships SET status='accepted', updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND friend_id=? AND status='pending'",
            (requester_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "Friend request accepted."
    except Exception as e:
        conn.close()
        return False, "Failed to accept friend request."

def decline_friend_request(user_id, requester_id):
    """Decline a friend request."""
    conn = get_db()
    try:
        # Remove the pending request
        conn.execute(
            "DELETE FROM friendships WHERE user_id=? AND friend_id=? AND status='pending'",
            (requester_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "Friend request declined."
    except Exception as e:
        conn.close()
        return False, "Failed to decline friend request."

def remove_friend(user_id, friend_id):
    """Remove a friend (or cancel pending request)."""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
            (user_id, friend_id, friend_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "Friend removed."
    except Exception as e:
        conn.close()
        return False, "Failed to remove friend."

def get_friends_list(user_id):
    """Get list of friends for a user."""
    conn = get_db()
    # Get accepted friends
    friends = conn.execute(
        """SELECT u.id, u.username 
           FROM users u
           JOIN friendships f ON (u.id = f.friend_id AND f.user_id = ?) OR (u.id = f.user_id AND f.friend_id = ?)
           WHERE f.status = 'accepted' AND u.id != ?""",
        (user_id, user_id, user_id)
    ).fetchall()
    conn.close()
    return [dict(f) for f in friends]

def get_friend_requests(user_id):
    """Get pending friend requests for a user."""
    conn = get_db()
    # Get incoming requests
    incoming = conn.execute(
        """SELECT u.id, u.username, f.created_at
           FROM users u
           JOIN friendships f ON u.id = f.user_id
           WHERE f.friend_id = ? AND f.status = 'pending'""",
        (user_id,)
    ).fetchall()
    
    # Get outgoing requests
    outgoing = conn.execute(
        """SELECT u.id, u.username, f.created_at
           FROM users u
           JOIN friendships f ON u.id = f.friend_id
           WHERE f.user_id = ? AND f.status = 'pending'""",
        (user_id,)
    ).fetchall()
    
    conn.close()
    return {
        "incoming": [dict(r) for r in incoming],
        "outgoing": [dict(r) for r in outgoing]
    }

def get_friendship_status(user_id, other_user_id):
    """Get friendship status between two users."""
    conn = get_db()
    friendship = conn.execute(
        "SELECT status FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
        (user_id, other_user_id, other_user_id, user_id)
    ).fetchone()
    conn.close()
    return friendship[0] if friendship else None

def search_users(query, current_user_id):
    """Search for users by username (excluding current user)."""
    conn = get_db()
    users = conn.execute(
        "SELECT id, username FROM users WHERE username LIKE ? AND id != ?",
        (f"%{query}%", current_user_id)
    ).fetchall()
    conn.close()
    return [dict(u) for u in users]


# ---- Private Rooms Management ----

def create_private_room(room_name, owner_id):
    """Create a private room and add the owner as a member."""
    conn = get_db()
    try:
        # Create the room
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rooms (name, is_private, owner_id) VALUES (?, 1, ?)",
            (room_name, owner_id)
        )
        room_id = cursor.lastrowid
        
        # Add owner as a member
        cursor.execute(
            "INSERT INTO room_members (room_id, user_id) VALUES (?, ?)",
            (room_id, owner_id)
        )
        
        conn.commit()
        conn.close()
        return True, "Private room created successfully.", room_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "A room with that name already exists.", None
    except Exception as e:
        conn.close()
        return False, f"Error creating room: {str(e)}", None


def get_user_private_rooms(user_id):
    """Get all private rooms the user is a member of."""
    conn = get_db()
    rows = conn.execute(
        """SELECT r.id, r.name, r.owner_id, r.created_at
           FROM rooms r
           JOIN room_members rm ON r.id = rm.room_id
           WHERE rm.user_id = ? AND r.is_private = 1
           ORDER BY r.created_at DESC""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_accessible_rooms(user_id):
    """Get all rooms the user can access (public rooms + private rooms they're in)."""
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT r.id, r.name, r.is_private, r.owner_id
           FROM rooms r
           LEFT JOIN room_members rm ON r.id = rm.room_id AND rm.user_id = ?
           WHERE r.is_private = 0 OR rm.user_id = ?
           ORDER BY r.name""",
        (user_id, user_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_room_members(room_id):
    """Get all members of a room."""
    conn = get_db()
    rows = conn.execute(
        """SELECT u.id, u.username
           FROM users u
           JOIN room_members rm ON u.id = rm.user_id
           WHERE rm.room_id = ?
           ORDER BY u.username""",
        (room_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_room_member(room_id, user_id):
    """Add a user to a room."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO room_members (room_id, user_id) VALUES (?, ?)",
            (room_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "Member added to room."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "User is already a member of this room."
    except Exception as e:
        conn.close()
        return False, f"Error adding member: {str(e)}"


def remove_room_member(room_id, user_id):
    """Remove a user from a room."""
    conn = get_db()
    try:
        # Can't remove owner from their own room
        room = conn.execute("SELECT owner_id FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room and room[0] == user_id:
            conn.close()
            return False, "Room owner cannot leave their own room."
        
        conn.execute(
            "DELETE FROM room_members WHERE room_id = ? AND user_id = ?",
            (room_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "Member removed from room."
    except Exception as e:
        conn.close()
        return False, f"Error removing member: {str(e)}"


def user_has_room_access(room_id, user_id):
    """Check if a user has access to a room."""
    conn = get_db()
    
    # Check if it's a public room
    public_check = conn.execute(
        "SELECT id FROM rooms WHERE id = ? AND is_private = 0",
        (room_id,)
    ).fetchone()
    
    if public_check:
        conn.close()
        return True
    
    # Check if user is a member of the private room
    member_check = conn.execute(
        "SELECT id FROM room_members WHERE room_id = ? AND user_id = ?",
        (room_id, user_id)
    ).fetchone()
    
    conn.close()
    return bool(member_check)


def invite_friend_to_room(room_id, friend_id, inviter_id):
    """Invite a friend to a private room."""
    conn = get_db()
    try:
        # Check if friend is already a member
        existing_member = conn.execute(
            "SELECT id FROM room_members WHERE room_id = ? AND user_id = ?",
            (room_id, friend_id)
        ).fetchone()
        
        if existing_member:
            conn.close()
            return False, "Friend is already a member of this room."
        
        # Create invitation
        conn.execute(
            "INSERT INTO room_invitations (room_id, user_id, inviter_id, status) VALUES (?, ?, ?, 'pending')",
            (room_id, friend_id, inviter_id)
        )
        conn.commit()
        conn.close()
        return True, "Invitation sent."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "An invitation already exists for this user."
    except Exception as e:
        conn.close()
        return False, f"Error sending invitation: {str(e)}"


def get_room_invitations(user_id):
    """Get pending room invitations for a user."""
    conn = get_db()
    rows = conn.execute(
        """SELECT ri.id, ri.room_id, r.name, u.id as inviter_id, u.username as inviter_username, ri.created_at
           FROM room_invitations ri
           JOIN rooms r ON ri.room_id = r.id
           JOIN users u ON ri.inviter_id = u.id
           WHERE ri.user_id = ? AND ri.status = 'pending'
           ORDER BY ri.created_at DESC""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def accept_room_invitation(invitation_id, user_id):
    """Accept a room invitation and add user to the room."""
    conn = get_db()
    try:
        # Get the invitation
        invitation = conn.execute(
            "SELECT room_id FROM room_invitations WHERE id = ? AND user_id = ?",
            (invitation_id, user_id)
        ).fetchone()
        
        if not invitation:
            conn.close()
            return False, "Invitation not found."
        
        room_id = invitation[0]
        
        # Add user to room
        conn.execute(
            "INSERT INTO room_members (room_id, user_id) VALUES (?, ?)",
            (room_id, user_id)
        )
        
        # Update invitation status
        conn.execute(
            "UPDATE room_invitations SET status = 'accepted' WHERE id = ?",
            (invitation_id,)
        )
        
        conn.commit()
        conn.close()
        return True, "Invitation accepted."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "You are already a member of this room."
    except Exception as e:
        conn.close()
        return False, f"Error accepting invitation: {str(e)}"


def decline_room_invitation(invitation_id, user_id):
    """Decline a room invitation."""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM room_invitations WHERE id = ? AND user_id = ?",
            (invitation_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "Invitation declined."
    except Exception as e:
        conn.close()
        return False, f"Error declining invitation: {str(e)}"


def user_has_room_access_by_name(room_name, user_id):
    """Check if a user has access to a room by room name."""
    conn = get_db()
    
    # Get room info
    room = conn.execute(
        "SELECT id, is_private FROM rooms WHERE name = ?",
        (room_name,)
    ).fetchone()
    
    if not room:
        conn.close()
        return False
    
    room_id = room[0]
    is_private = room[1]
    
    # Public rooms are always accessible
    if is_private == 0:
        conn.close()
        return True
    
    # For private rooms, check membership
    member = conn.execute(
        "SELECT id FROM room_members WHERE room_id = ? AND user_id = ?",
        (room_id, user_id)
    ).fetchone()
    
    conn.close()
    return bool(member)
