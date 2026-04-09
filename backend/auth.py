"""
auth.py  –  Session & authentication helpers for GuardianText
"""

import re
import logging
from functools import wraps
from flask import session, jsonify

logger = logging.getLogger(__name__)

# ── Validation ────────────────────────────────────────────────────────────────

def validate_username(username: str):
    """Validate username format and length"""
    if not username:
        return False, "Username is required."
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 20:
        return False, "Username must be 20 characters or fewer."
    if not re.match(r'^[A-Za-z0-9_]+$', username):
        return False, "Username may only contain letters, numbers, and underscores."
    return True, ""

def validate_password(password: str):
    """Validate password strength"""
    if not password:
        return False, "Password is required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if len(password) > 128:
        return False, "Password is too long."
    return True, ""

def validate_room_name(room_name: str):
    """Validate room name"""
    if not room_name:
        return False, "Room name is required."
    room_name = room_name.strip()
    if len(room_name) < 2:
        return False, "Room name must be at least 2 characters."
    if len(room_name) > 50:
        return False, "Room name must be 50 characters or fewer."
    return True, ""

def validate_message(message: str):
    """Validate message content"""
    if not message:
        return False, "Message cannot be empty."
    if len(message) > 5000:
        return False, "Message is too long (max 5000 characters)."
    return True, ""

# ── Decorators ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Unauthorized access attempt")
            return jsonify({"error": "Authentication required.", "redirect": "/"}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator requiring admin privileges"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Admin access denied: not logged in")
            return jsonify({"error": "Authentication required.", "redirect": "/"}), 401
        if not session.get('is_admin'):
            logger.warning(f"Admin access denied for user {session.get('user_id')}")
            return jsonify({"error": "Admin privileges required."}), 403
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    """Get current user from session"""
    return {
        "id": session.get("user_id"),
        "username": session.get("username"),
        "is_admin": session.get("is_admin", False)
    } if "user_id" in session else None
