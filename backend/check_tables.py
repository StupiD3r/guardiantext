from database import get_db

conn = get_db()
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [table[0] for table in tables])

# Check if friendships table exists specifically
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='friendships'")
friendships_exists = cursor.fetchone()
print('Friendships table exists:', friendships_exists is not None)

if friendships_exists:
    cursor.execute("SELECT * FROM friendships")
    friendships = cursor.fetchall()
    print('Friendships data:', friendships)

conn.close()
