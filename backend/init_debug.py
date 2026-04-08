from database import init_db, get_db
import sqlite3

try:
    print("Running init_db...")
    init_db()
    print("init_db completed")
    
    # Check if tables exist
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables created:", tables)
    
    conn.close()
    
except Exception as e:
    print(f"Error during init_db: {e}")
    import traceback
    traceback.print_exc()
