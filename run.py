#!/usr/bin/env python3
"""
run.py  –  GuardianText launcher

Usage:
    python run.py

This will:
  - start the backend server (which serves the frontend)
  - automatically open the app in your default browser
"""
import sys
import os
import threading
import time
import webbrowser

# Add backend to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
sys.path.insert(0, BACKEND_DIR)

from app import socketio, app  # type: ignore  # imported from backend
from config import Config      # type: ignore


def _open_browser():
    """Open the app in the default browser after a short delay."""
    # Small delay so the server has time to start listening
    time.sleep(2)
    url = f"http://localhost:{Config.PORT}"
    try:
        webbrowser.open(url, new=1)
    except Exception:
        # Fallback: ignore failures – user can open manually
        pass


if __name__ == '__main__':
    # Launch browser in background
    threading.Thread(target=_open_browser, daemon=True).start()

    # Start Socket.IO / Flask backend (serves the frontend)
    socketio.run(app, host=Config.HOST, port=Config.PORT,
                 debug=Config.DEBUG, allow_unsafe_werkzeug=True)
