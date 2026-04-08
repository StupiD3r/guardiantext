import sqlite3

conn = sqlite3.connect('guardiantext.db')
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', tables)

# Check users
cursor.execute("SELECT id, username FROM users")
users = cursor.fetchall()
print('Users:', users)

# Check friendships
try:
    cursor.execute("SELECT * FROM friendships")
    friendships = cursor.fetchall()
    print('Friendships:', friendships)
except sqlite3.OperationalError as e:
    print('Friendships table error:', e)

conn.close()
