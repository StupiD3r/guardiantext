#!/usr/bin/env python3
"""Clean up old database to force migration on app restart."""

import os
import sys

db_path = os.path.join(os.path.dirname(__file__), 'guardiantext.db')

if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"✅ Deleted old database: {db_path}")
        print("App will recreate it with bcrypt on next start.")
    except Exception as e:
        print(f"❌ Error deleting database: {e}")
        sys.exit(1)
else:
    print("Database not found, nothing to delete.")

sys.exit(0)
