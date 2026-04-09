import sqlite3
import hashlib
import os
import sys
import bcrypt
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'guardiantext.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash password using bcrypt (secure for storage)"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    return bcrypt.hashpw(password, bcrypt.gensalt(rounds=12)).decode('utf-8')

def verify_password(password, password_hash):
    """Verify password against bcrypt hash"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    if isinstance(password_hash, str):
        password_hash = password_hash.encode('utf-8')
    try:
        return bcrypt.checkpw(password, password_hash)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

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
    
    # Add profile columns (profile picture and status)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_picture TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Available'")
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
                role        TEXT DEFAULT 'member',
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(room_id, user_id)
            );
        ''')
    except sqlite3.OperationalError:
        pass
    
    # Migrate existing room_members to add role column if needed
    try:
        cursor.execute("PRAGMA table_info(room_members)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'role' not in columns:
            logger.info("Adding role column to room_members table...")
            cursor.execute("ALTER TABLE room_members ADD COLUMN role TEXT DEFAULT 'member'")
            # Set room owners as admins
            cursor.execute("""
                UPDATE room_members SET role = 'admin'
                WHERE room_id IN (SELECT id FROM rooms WHERE owner_id = room_members.user_id)
            """)
            conn.commit()
    except Exception as e:
        logger.warning(f"Migration error (non-critical): {e}")
    
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
    
    # Create indexes for performance
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_room_members_room_user ON room_members(room_id, user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friendships_user ON friendships(user_id, friend_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_filter_logs_user_timestamp ON filter_logs(user_id, timestamp)")
        logger.info("Database indexes created/verified")
    except Exception as e:
        logger.warning(f"Index creation error (non-critical): {e}")
    
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
        logger.info(f"User created: {username}")
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        logger.warning(f"User creation failed: username already taken - {username}")
        return False, "Username already taken."
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False, "An error occurred during registration."
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        
        if row and verify_password(password, row['password_hash']):
            logger.info(f"User login successful: {username}")
            return True, dict(row)
        
        logger.warning(f"Failed login attempt for: {username}")
        return False, None
    except Exception as e:
        logger.error(f"Error verifying user: {e}")
        return False, None
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Get user by ID."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching user by ID: {e}")
        return None
    finally:
        conn.close()

def change_password(user_id, old_password, new_password):
    """Change user password after verification."""
    conn = get_db()
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
        
        if not row or not verify_password(old_password, row['password_hash']):
            logger.warning(f"Password change failed: wrong old password for user {user_id}")
            return False, "Current password is incorrect."
        
        new_hash = hash_password(new_password)
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
        conn.commit()
        logger.info(f"Password changed for user {user_id}")
        return True, "Password changed successfully."
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_user_profile(user_id):
    """Get user profile (public info)."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username, profile_picture, status, created_at FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return None
    finally:
        conn.close()

def update_user_profile(user_id, profile_picture=None, status=None):
    """Update user profile (picture and/or status)."""
    conn = get_db()
    try:
        if profile_picture is not None:
            conn.execute("UPDATE users SET profile_picture=? WHERE id=?", (profile_picture, user_id))
        if status is not None:
            conn.execute("UPDATE users SET status=? WHERE id=?", (status[:100], user_id))  # Max 100 chars
        conn.commit()
        logger.info(f"Profile updated for user {user_id}")
        return True, "Profile updated successfully."
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return False, str(e)
    finally:
        conn.close()
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def ensure_default_admin():
    """
    Ensure there is at least one admin user.
    Creates a default 'admin' account with password 'admin123' if none exists.
    Also updates old SHA256 passwords to bcrypt if found.
    """
    conn = get_db()
    cur = conn.cursor()
    
    # Check if any admin exists
    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin=1")
    has_admin = cur.fetchone()[0] > 0
    
    if not has_admin:
        # No admin exists, try to create or promote one
        cur.execute("SELECT id FROM users WHERE username='admin'")
        existing = cur.fetchone()
        if existing:
            # Admin user exists, just promote them
            cur.execute("UPDATE users SET is_admin=1 WHERE id=?", (existing[0],))
            admin_id = existing[0]
        else:
            # Create new admin user
            cur.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                ("admin", hash_password("admin123")),
            )
            admin_id = cur.lastrowid
    else:
        # Admin exists, check if password is old SHA256 format (needs migration)
        cur.execute("SELECT id, password_hash FROM users WHERE username='admin'")
        admin = cur.fetchone()
        if admin and not admin['password_hash'].startswith('$2'):
            # Old SHA256 hash detected, update to bcrypt
            logger.info("Migrating admin password from SHA256 to bcrypt")
            cur.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                (hash_password("admin123"), admin['id'])
            )
    
    conn.commit()
    conn.close()
    logger.info("Default admin user ensured")


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
    """Create a private room and add the owner as an admin member."""
    conn = get_db()
    try:
        # Create the room
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rooms (name, is_private, owner_id) VALUES (?, 1, ?)",
            (room_name, owner_id)
        )
        room_id = cursor.lastrowid
        
        # Add owner as an admin member
        cursor.execute(
            "INSERT INTO room_members (room_id, user_id, role) VALUES (?, ?, 'admin')",
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
    """Get all members of a room with their roles."""
    conn = get_db()
    rows = conn.execute(
        """SELECT u.id, u.username, COALESCE(rm.role, 'member') as role
           FROM users u
           JOIN room_members rm ON u.id = rm.user_id
           WHERE rm.room_id = ?
           ORDER BY rm.role DESC, u.username""",
        (room_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_room_member(room_id, user_id, role='member'):
    """Add a user to a room with specified role."""
    if role not in ['admin', 'member']:
        return False, "Invalid role. Must be 'admin' or 'member'."
    
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO room_members (room_id, user_id, role) VALUES (?, ?, ?)",
            (room_id, user_id, role)
        )
        conn.commit()
        conn.close()
        logger.info(f"Member {user_id} added to room {room_id} with role {role}")
        return True, "Member added to room."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "User is already a member of this room."
    except Exception as e:
        conn.close()
        logger.error(f"Error adding member: {e}")
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


def get_user_room_role(room_id, user_id):
    """Get the role of a user in a room (admin, member, or None)."""
    conn = get_db()
    row = conn.execute(
        "SELECT role FROM room_members WHERE room_id = ? AND user_id = ?",
        (room_id, user_id)
    ).fetchone()
    conn.close()
    return row['role'] if row else None

def is_room_admin(room_id, user_id):
    """Check if user is an admin of the room."""
    role = get_user_room_role(room_id, user_id)
    return role == 'admin'

def promote_to_admin(room_id, user_id, promoted_by_id):
    """Promote a member to admin (admin only)."""
    if not is_room_admin(room_id, promoted_by_id):
        return False, "You must be an admin to promote members."
    
    conn = get_db()
    try:
        conn.execute(
            "UPDATE room_members SET role = 'admin' WHERE room_id = ? AND user_id = ?",
            (room_id, user_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"User {user_id} promoted to admin in room {room_id} by {promoted_by_id}")
        return True, "Member promoted to admin."
    except Exception as e:
        conn.close()
        logger.error(f"Error promoting member: {e}")
        return False, f"Error promoting member: {str(e)}"

def demote_to_member(room_id, user_id, demoted_by_id):
    """Demote an admin to member (admin only)."""
    if not is_room_admin(room_id, demoted_by_id):
        return False, "You must be an admin to demote members."
    
    # Prevent owner from being demoted
    room = get_db().execute("SELECT owner_id FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room and room['owner_id'] == user_id:
        return False, "Cannot demote the room owner."
    
    conn = get_db()
    try:
        conn.execute(
            "UPDATE room_members SET role = 'member' WHERE room_id = ? AND user_id = ?",
            (room_id, user_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"User {user_id} demoted to member in room {room_id}")
        return True, "Member demoted to member role."
    except Exception as e:
        conn.close()
        logger.error(f"Error demoting member: {e}")
        return False, f"Error demoting member: {str(e)}"

def kick_member(room_id, user_id, kicked_by_id):
    """Kick a member from the room (admin only)."""
    if not is_room_admin(room_id, kicked_by_id):
        return False, "You must be an admin to kick members."
    
    # Prevent owner from being kicked
    room = get_db().execute("SELECT owner_id FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room and room['owner_id'] == user_id:
        return False, "Cannot kick the room owner."
    
    return remove_room_member(room_id, user_id)

def delete_room(room_id, deleted_by_id):
    """Delete a room (admin/owner only)."""
    if not is_room_admin(room_id, deleted_by_id):
        return False, "You must be an admin to delete the room."
    
    conn = get_db()
    try:
        # Delete all messages in the room
        conn.execute("DELETE FROM messages WHERE room = (SELECT name FROM rooms WHERE id = ?)", (room_id,))
        # Delete all room members
        conn.execute("DELETE FROM room_members WHERE room_id = ?", (room_id,))
        # Delete all room invitations
        conn.execute("DELETE FROM room_invitations WHERE room_id = ?", (room_id,))
        # Delete the room
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        conn.commit()
        conn.close()
        logger.info(f"Room {room_id} deleted by {deleted_by_id}")
        return True, "Room deleted successfully."
    except Exception as e:
        conn.close()
        logger.error(f"Error deleting room: {e}")
        return False, f"Error deleting room: {str(e)}"

def update_room_name(room_id, new_name, updated_by_id):
    """Update room name (admin/owner only, or any member)."""
    # Allow any member to update room name (based on requirement)
    role = get_user_room_role(room_id, updated_by_id)
    if role is None:
        return False, "You are not a member of this room."
    
    # Validate room name
    if not new_name or len(new_name) < 2:
        return False, "Room name must be at least 2 characters."
    if len(new_name) > 50:
        return False, "Room name must be 50 characters or fewer."
    
    conn = get_db()
    try:
        conn.execute(
            "UPDATE rooms SET name = ? WHERE id = ?",
            (new_name, room_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Room {room_id} name updated to '{new_name}' by {updated_by_id}")
        return True, "Room name updated."
    except Exception as e:
        conn.close()
        logger.error(f"Error updating room name: {e}")
        return False, f"Error updating room name: {str(e)}"

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
