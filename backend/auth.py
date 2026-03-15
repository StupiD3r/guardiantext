"""
auth.py  –  Session & authentication helpers for GuardianText
"""

import re
from functools import wraps
from flask import session, jsonify

# ── Validation ────────────────────────────────────────────────────────────────

def validate_username(username: str):
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 20:
        return False, "Username must be 20 characters or fewer."
    if not re.match(r'^[A-Za-z0-9_]+$', username):
        return False, "Username may only contain letters, numbers, and underscores."
    return True, ""

def validate_password(password: str):
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters."
    return True, ""

# ── Decorators ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required.", "redirect": "/"}), 401
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    return {
        "id": session.get("user_id"),
        "username": session.get("username"),
    } if "user_id" in session else None
