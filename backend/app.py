"""
app.py  –  GuardianText  |  Main Flask + Socket.IO Application
──────────────────────────────────────────────────────────────
Run:  python app.py
Access from other PCs:  http://<this-machine-ip>:5000
"""

import os
import sys
import re

# Make sure local modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import (Flask, render_template, request,
                   session, jsonify, redirect, url_for, send_from_directory)
from flask_socketio import SocketIO, join_room, leave_room, emit
from datetime import datetime

from config import Config
from database import (init_db, create_user, verify_user, save_message,
                      get_room_messages, log_filter_event,
                      get_filter_logs, get_user_filter_logs,
                      get_dashboard_stats, get_db,
                      get_user_by_id, ensure_default_admin,
                      set_user_banned, get_user_toxicity_overview,
                      set_user_password, get_recent_messages,
                      delete_message, clear_all_messages)
from auth import validate_username, validate_password, login_required, get_current_user
from nlp_filter import analyze_message, FilterResult
from learning_suggestions import generate_ml_suggestions, learn_from_user_choice
from enhanced_ml_system import detect_enhanced_context, get_enhanced_context_suggestions

# ── App setup ─────────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.config['SECRET_KEY'] = Config.SECRET_KEY

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

init_db()
ensure_default_admin()

# Keep track of users currently online: {room: [username, ...]}
online_users: dict = {}

def _create_filtered_version(original: str, toxic_words: list) -> str:
    """Create a filtered version by removing toxic words but keeping structure."""
    if not toxic_words:
        return original
    
    filtered = original
    
    # Enhanced word removal - handle variations and contractions
    for word in sorted(toxic_words, key=len, reverse=True):
        # Remove the toxic word and all its variations
        # Handle cases like "fuck" in "fucked", "fucking", etc.
        pattern = r'\b' + re.escape(word) + r'(?:ed|ing|er|s)\b'
        filtered = re.sub(pattern, '', filtered, flags=re.IGNORECASE)
        
        # Also handle cases where word is part of contraction (like "we're fucked")
        # Look for word patterns that might not have word boundaries
        if word.lower() == 'fuck':
            # Special handling for "fuck" variations
            filtered = re.sub(r'\bfuck(?:ed|ing|er|s)\b', '', filtered, flags=re.IGNORECASE)
            filtered = re.sub(r'\bfucks?\b', '', filtered, flags=re.IGNORECASE)
        elif word.lower() == 'shit':
            filtered = re.sub(r'\bshit(?:s|ty|ted|ting)\b', '', filtered, flags=re.IGNORECASE)
        elif word.lower() == 'stupid':
            filtered = re.sub(r'\bstupid(?:ly)?\b', '', filtered, flags=re.IGNORECASE)
    
    # Clean up extra spaces and punctuation
    filtered = re.sub(r'\s+', ' ', filtered)  # Collapse multiple spaces
    filtered = re.sub(r'\s*([,.!?])\s*', r'\1', filtered)  # Fix spacing around punctuation
    filtered = re.sub(r'\s+', ' ', filtered).strip()  # Final cleanup
    
    # Remove any remaining toxic substrings (fallback)
    for word in toxic_words:
        if word.lower() in filtered.lower():
            # Remove any remaining instances
            filtered = re.sub(re.escape(word), '', filtered, flags=re.IGNORECASE)
    
    # Final cleanup again
    filtered = re.sub(r'\s+', ' ', filtered).strip()
    
    # Capitalize first letter
    if filtered:
        filtered = filtered[0].upper() + filtered[1:]
    
    return filtered

def _generate_alternative_paraphrase(text: str, toxic_words: list) -> str:
    """Generate a second paraphrase option with different wording."""
    if not toxic_words:
        return text
    
    text_lower = text.lower()
    
    # School context alternatives
    if any(word in text_lower for word in ['school', 'teacher', 'homework', 'exam', 'class']):
        if any(toxic in text_lower for toxic in ['fucking', 'shit', 'crap', 'sucks']):
            return "I'm finding this school work really challenging."
        if any(toxic in text_lower for toxic in ['stupid', 'dumb', 'idiot']):
            return "I don't quite understand what we're learning."
        return "This is difficult for me to grasp."
    
    # Personal disagreement alternatives
    if any(toxic in text_lower for toxic in ['stupid', 'idiot', 'dumb', 'moron', 'loser']):
        return "I have a completely different perspective on this."
    
    # Frustration alternatives  
    if any(toxic in text_lower for toxic in ['fuck', 'shit', 'crap', 'damn']):
        return "This situation is making me feel frustrated."
    
    # Strong disagreement
    if 'hate' in text_lower:
        return "I really don't agree with this approach."
    
    # Default alternative
    return "Let's try to find a better way to handle this."

def _generate_contextual_alternative(text: str, toxic_words: list) -> str:
    """Generate a flexible fourth option based on context."""
    if not toxic_words:
        return text
    
    text_lower = text.lower()
    
    # Work/professional context
    if any(word in text_lower for word in ['work', 'job', 'boss', 'project', 'deadline']):
        return "I'd like to discuss how we can improve this situation."
    
    # Personal relationships
    if any(word in text_lower for word in ['you', 'your', 'friend', 'family']):
        return "I value our relationship and want to communicate better."
    
    # General conflict
    if any(toxic in text_lower for toxic in ['stupid', 'idiot', 'dumb']):
        return "I think we're having trouble understanding each other."
    
    # High frustration
    if any(toxic in text_lower for toxic in ['fuck', 'shit', 'crap']):
        return "I need to take a moment to collect my thoughts."
    
    # Default flexible option
    return "Let's approach this more constructively."

def _generate_contextual_suggestion(text: str, toxic_words: list) -> str:
    """Generate contextual suggestions based on message content and toxic words."""
    text_lower = text.lower()
    
    # School/education context
    if any(word in text_lower for word in ['school', 'teacher', 'homework', 'exam', 'class']):
        if any(toxic in toxic_words for toxic in ['fucking', 'hate']):
            return "I'm having a really hard time with school right now."
        if any(toxic in toxic_words for toxic in ['stupid', 'dumb']):
            return "I don't understand what we're learning in class."
    
    # Personal disagreement
    if any(toxic in toxic_words for toxic in ['stupid', 'idiot', 'dumb', 'moron']):
        return "I see things completely differently than you do."
    
    # General frustration
    if any(toxic in toxic_words for toxic in ['fuck', 'shit', 'crap', 'damn']):
        return "I'm feeling really frustrated about this situation."
    
    # Strong disagreement
    if 'hate' in toxic_words:
        return "I strongly disagree with this approach."
    
    # Default constructive response
    return "I'd like to share my thoughts on this respectfully."

# ── Static file routes ────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/chat.html')
    return send_from_directory(FRONTEND_DIR, 'login.html')

@app.route('/dashboard')
def dashboard_page():
    if 'user_id' not in session:
        return redirect('/')
    return send_from_directory(FRONTEND_DIR, 'dashboard.html')

# ── Auth API ──────────────────────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    ok, msg = validate_username(username)
    if not ok:
        return jsonify({"success": False, "message": msg}), 400

    ok, msg = validate_password(password)
    if not ok:
        return jsonify({"success": False, "message": msg}), 400

    success, msg = create_user(username, password)
    return jsonify({"success": success, "message": msg}), (201 if success else 409)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    success, user = verify_user(username, password)
    if not success:
        return jsonify({"success": False, "message": "Invalid credentials."}), 401

    session['user_id']  = user['id']
    session['username'] = user['username']
    session['is_admin'] = user.get('is_admin', 0)
    return jsonify({"success": True, "username": user['username']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/me')
def me():
    user = get_current_user()
    if not user:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, **user})

# ── Chat API ──────────────────────────────────────────────────────────────────

@app.route('/api/rooms')
@login_required
def get_rooms():
    conn = get_db()
    rows = conn.execute("SELECT name FROM rooms ORDER BY name").fetchall()
    conn.close()
    return jsonify({"rooms": [r['name'] for r in rows]})

@app.route('/api/messages/<room>')
@login_required
def get_messages(room):
    msgs = get_room_messages(room, limit=80)
    return jsonify({"messages": msgs})

# ── Dashboard API ─────────────────────────────────────────────────────────────

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    return jsonify(get_dashboard_stats())

@app.route('/api/dashboard/logs')
@login_required
def dashboard_logs():
    user_only = request.args.get('mine') == 'true'
    if user_only:
        logs = get_user_filter_logs(session['user_id'])
    else:
        logs = get_filter_logs()
    return jsonify({"logs": logs})


# ── Admin API ────────────────────────────────────────────────────────────────────

@app.route("/api/admin/users")
@login_required
def admin_users():
    if not session.get("is_admin"):
        return jsonify({"error": "Admin privileges required"}), 403
    users = get_user_toxicity_overview()
    return jsonify({"users": users})


@app.route("/api/admin/users/<int:user_id>/ban", methods=["POST"])
@login_required
def admin_ban_user(user_id: int):
    if not session.get("is_admin"):
        return jsonify({"error": "Admin privileges required"}), 403
    data = request.get_json(silent=True) or {}
    banned = bool(data.get("banned", True))
    if session.get("user_id") == user_id:
        return jsonify({"error": "You cannot ban yourself."}), 400
    set_user_banned(user_id, banned)
    return jsonify({"success": True, "user_id": user_id, "banned": banned})


@app.route("/api/admin/users/<int:user_id>/reset_password", methods=["POST"])
@login_required
def admin_reset_password(user_id: int):
    if not session.get("is_admin"):
        return jsonify({"error": "Admin privileges required"}), 403
    data = request.get_json(silent=True) or {}
    new_password = (data.get("new_password") or "").strip()
    ok, msg = validate_password(new_password)
    if not ok:
        return jsonify({"error": msg}), 400
    if session.get("user_id") == user_id:
        # Allow self-reset but this is still via admin endpoint
        pass
    set_user_password(user_id, new_password)
    return jsonify({"success": True})


@app.route("/api/admin/messages", methods=["GET", "DELETE"])
@login_required
def admin_messages():
    if not session.get("is_admin"):
        return jsonify({"error": "Admin privileges required"}), 403
    if request.method == "DELETE":
        clear_all_messages(include_logs=True)
        return jsonify({"success": True})
    # GET – list recent messages
    messages = get_recent_messages(limit=200)
    return jsonify({"messages": messages})


@app.route("/api/admin/messages/<int:message_id>", methods=["DELETE"])
@login_required
def admin_delete_message(message_id: int):
    if not session.get("is_admin"):
        return jsonify({"error": "Admin privileges required"}), 403
    delete_message(message_id)
    return jsonify({"success": True, "message_id": message_id})

# ── Socket.IO events ──────────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    user = get_current_user()
    if not user:
        return False   # Reject unauthenticated socket connections
    print(f"[WS] {user['username']} connected  sid={request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    username = session.get('username', 'Unknown')
    # Remove from all rooms
    for room, users in list(online_users.items()):
        if username in users:
            users.remove(username)
            emit('user_left', {'username': username, 'room': room,
                               'online_count': len(users)},
                 room=room)
    print(f"[WS] {username} disconnected")

@socketio.on('join_room')
def on_join(data):
    room = data.get('room', 'General')
    username = session.get('username')
    if not username:
        return

    join_room(room)
    if room not in online_users:
        online_users[room] = []
    if username not in online_users[room]:
        online_users[room].append(username)

    emit('room_joined', {
        'room': room,
        'online_users': online_users[room],
        'online_count': len(online_users[room])
    })
    emit('user_joined', {
        'username': username,
        'room': room,
        'online_users': online_users[room],
        'online_count': len(online_users[room])
    }, room=room, include_self=False)

    print(f"[WS] {username} joined room '{room}'")

@socketio.on('leave_room')
def on_leave(data):
    room = data.get('room', 'General')
    username = session.get('username')
    if not username:
        return

    leave_room(room)
    if room in online_users and username in online_users[room]:
        online_users[room].remove(username)

    emit('user_left', {
        'username': username,
        'room': room,
        'online_users': online_users.get(room, []),
        'online_count': len(online_users.get(room, []))
    }, room=room)

@socketio.on('send_message')
def on_message(data):
    user_id  = session.get('user_id')
    username = session.get('username')
    room     = data.get('room', 'General')
    text     = (data.get('message') or '').strip()

    if not username or not text:
        return

    # Block banned users from sending any messages
    user = get_user_by_id(user_id) if user_id else None
    if user and user.get("is_banned"):
        emit(
            "user_banned",
            {
                "reason": "You have been restricted from sending messages due to repeated toxic behavior.",
            },
        )
        return

    # ── True ML Toxicity Analysis ───────────────────────────────────────────────────
    # Use True ML system for intelligent toxicity detection
    try:
        from true_ml_toxicity import analyze_with_true_ml
        ml_result = analyze_with_true_ml(text)
        
        # Convert True ML result to expected format
        result = FilterResult(
            is_toxic=ml_result.is_toxic,
            toxicity_score=ml_result.toxicity_score,
            severity=0 if ml_result.severity == 'mild' else 1 if ml_result.severity == 'moderate' else 2,
            toxic_words=[tw.word for tw in ml_result.toxic_words],
            cleaned_message=ml_result.clean_suggestion,
            suggestion=ml_result.clean_suggestion,
            action='blocked' if ml_result.toxicity_score > 0.7 else 'warned' if ml_result.toxicity_score > 0.3 else 'allowed',
            original_message=text
        )
    except Exception as e:
        print(f"True ML error: {e}, falling back to legacy system")
        # Fallback to legacy NLP analysis
        result = analyze_message(
            text,
            block_threshold=Config.BLOCK_THRESHOLD,
            warn_threshold=Config.TOXICITY_THRESHOLD,
        )

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Extract toxic words using True ML system for better accuracy
    toxic_words_for_filtering = []
    try:
        from true_ml_toxicity import analyze_with_true_ml
        ml_analysis = analyze_with_true_ml(text)
        toxic_words_for_filtering = [tw.word for tw in ml_analysis.toxic_words]
    except:
        # Fallback to original result if True ML fails
        toxic_words_for_filtering = result.toxic_words

    # If message is toxic (warned or blocked) AND has toxic words, do not send immediately.
    # Instead, send enhanced ML-generated suggestions back to the sender.
    if result.action in ("warned", "blocked") and toxic_words_for_filtering:
        # Generate enhanced ML-based suggestions
        user_id = session.get('user_id')
        
        # Generate filtered version (toxic words removed) using True ML words
        filtered_version = _create_filtered_version(text, toxic_words_for_filtering)
        
        # Get ML-generated suggestions for options 2 and 3 using True ML system
        ml_suggestions = []
        try:
            # Use True ML system to generate intelligent suggestions
            from true_ml_toxicity import analyze_with_true_ml
            
            # Get True ML analysis for better understanding
            ml_result = analyze_with_true_ml(text)
            
            # Extract toxic words from True ML result
            true_toxic_words = [tw.word for tw in ml_result.toxic_words]
            
            # Generate suggestions based on True ML clean suggestion and trained data
            if ml_result.clean_suggestion and ml_result.clean_suggestion != text:
                # Use True ML's clean suggestion as primary option
                ml_suggestions.append({
                    "text": ml_result.clean_suggestion,
                    "type": "true_ml_clean",
                    "confidence": ml_result.confidence
                })
            
            # Try to get additional suggestions from trained ML data
            try:
                from enhanced_ml_system import get_enhanced_context_suggestions, detect_enhanced_context
                context = detect_enhanced_context(text, true_toxic_words)
                enhanced_suggestions = get_enhanced_context_suggestions(context, text)
                
                for sugg in enhanced_suggestions[:2]:  # Get up to 2 more
                    if sugg and sugg != ml_result.clean_suggestion:
                        ml_suggestions.append({
                            "text": sugg,
                            "type": "enhanced_context",
                            "confidence": 0.8
                        })
            except Exception as e:
                print(f"Enhanced ML error: {e}")
                
        except Exception as e:
            print(f"True ML error: {e}")
            # Fallback to original ML system
            try:
                ml_suggestions = generate_ml_suggestions(user_id or 0, text, toxic_words_for_filtering)
                # Convert to new format
                if isinstance(ml_suggestions, list):
                    ml_suggestions = [{"text": s, "type": "fallback", "confidence": 0.6} for s in ml_suggestions]
                else:
                    ml_suggestions = []
            except Exception as e2:
                print(f"Original ML error: {e2}")
                ml_suggestions = []
        
        # If we don't have enough ML suggestions, use enhanced ML as backup
        if len(ml_suggestions) < 2:
            try:
                enhanced_context = detect_enhanced_context(text, toxic_words_for_filtering)
                enhanced_suggestions = get_enhanced_context_suggestions(enhanced_context, text)
                # Convert enhanced suggestions to the expected format
                for sugg in enhanced_suggestions:
                    if len(ml_suggestions) >= 2:
                        break
                    if not any(opt.get("text", "") == sugg for opt in ml_suggestions):
                        ml_suggestions.append({
                            "text": sugg,
                            "type": f"enhanced_{len(ml_suggestions)}",
                            "confidence": 0.7
                        })
            except Exception as e:
                pass
        
        # Create exactly 4 options as specified
        options = [
            {
                "id": "filtered",
                "label": "Same sentence without toxic words",
                "text": filtered_version,
                "hint": "Original sentence structure preserved"
            }
        ]
        
        # Add ML suggestions as options 2 and 3
        if len(ml_suggestions) >= 1:
            options.append({
                "id": "ml_paraphrase1",
                "label": "ML-generated paraphrase",
                "text": ml_suggestions[0]["text"],
                "hint": "Machine learning rephrasing",
                "confidence": ml_suggestions[0].get("confidence", 0.8)
            })
        
        if len(ml_suggestions) >= 2:
            options.append({
                "id": "ml_paraphrase2", 
                "label": "Alternative ML paraphrase",
                "text": ml_suggestions[1]["text"],
                "hint": "Alternative ML rephrasing",
                "confidence": ml_suggestions[1].get("confidence", 0.8)
            })
        
        # If we don't have enough ML suggestions, add fallback paraphrases
        if len(options) < 3:
            paraphrase1 = result.cleaned_message  # Natural rephrasing from NLP filter
            options.append({
                "id": "paraphrase1",
                "label": "Paraphrased version",
                "text": paraphrase1,
                "hint": "Rephrased to be non-toxic"
            })
        
        if len(options) < 4:
            paraphrase2 = _generate_alternative_paraphrase(text, result.toxic_words)
            options.append({
                "id": "paraphrase2",
                "label": "Alternative paraphrase", 
                "text": paraphrase2,
                "hint": "Different non-toxic phrasing"
            })
        
        # Add flexible fourth option
        fourth_option = _generate_contextual_alternative(text, result.toxic_words)
        if len(options) < 4:
            options.append({
                "id": "flexible",
                "label": "Alternative option",
                "text": fourth_option,
                "hint": "Contextual alternative"
            })
        
        # Ensure we have exactly 4 options
        options = options[:4]

        emit(
            "message_suggestions",
            {
                "room": room,
                "original_message": text,
                "toxicity_score": result.toxicity_score,
                "toxic_words": toxic_words_for_filtering,  # Use True ML detected words
                "severity": result.severity,
                "suggestion_text": result.suggestion,
                "decision": result.action,
                "options": options,
            },
        )
        return

    # Clean / non-toxic message – broadcast as-is
    save_message(user_id, username, room, text)
    socketio.emit(
        "new_message",
        {
            "id": None,
            "sender_username": username,
            "room": room,
            "content": text,
            "is_filtered": False,
            "toxicity_score": 0.0,
            "timestamp": timestamp,
        },
        room=room,
    )

@socketio.on("confirm_message")
def on_confirm_message(data):
    user_id = session.get('user_id')
    username = session.get('username')
    room = data.get('room', 'General')
    message = data.get('message')
    original_message = data.get('original_message')
    toxic_words = data.get('toxic_words', [])
    suggestion_type = data.get('suggestion_type', 'unknown')
    suggested_text = data.get('suggested_text', '')
    
    # Learn from user choice
    if original_message and toxic_words and suggestion_type:
        user_choice = 'accepted' if message != original_message else 'rejected'
        try:
            learn_from_user_choice(
                user_id or 0, original_message, toxic_words, 
                suggestion_type, suggested_text, user_choice
            )
        except Exception as e:
            print(f"Error in ML learning feedback: {e}")
    
    # Save the chosen message
    if not username or not message:
        return

    # Block banned users from sending any messages
    user = get_user_by_id(user_id) if user_id else None
    if user and user.get("is_banned"):
        emit(
            "user_banned",
            {
                "reason": "You have been restricted from sending messages due to repeated toxic behavior.",
            },
        )
        return

    action = data.get('decision', 'allowed')
    toxicity_score = data.get('toxicity_score', 0.0)
    
    save_message(
        user_id,
        username,
        room,
        message,
        is_filtered=(action != 'allowed'),
        original_content=original_message,
        toxicity_score=toxicity_score,
        toxic_words=toxic_words
    )

    emit('new_message', {
        'id': None,
        'sender_username': username,
        'room': room,
        'content': message,
        'is_filtered': (action != 'allowed'),
        'toxicity_score': toxicity_score,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
    }, room=room)

@socketio.on('typing')
def on_typing(data):
    room     = data.get('room', 'General')
    username = session.get('username')
    is_typing = data.get('typing', False)
    emit('user_typing', {'username': username, 'typing': is_typing},
         room=room, include_self=False)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'

    print("=" * 60)
    print("  GuardianText  –  Context-Aware Messaging Application")
    print("=" * 60)
    print(f"  Local access:    http://localhost:{Config.PORT}")
    print(f"  Network access:  http://{local_ip}:{Config.PORT}")
    print("  Share the Network URL with other PCs on the same network.")
    print("=" * 60)

    socketio.run(app, host=Config.HOST, port=Config.PORT,
                 debug=Config.DEBUG, allow_unsafe_werkzeug=True)
