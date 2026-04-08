from database import get_db

conn = get_db()
cursor = conn.cursor()

# Check friendships data
cursor.execute("SELECT * FROM friendships")
friendships = cursor.fetchall()
print('Friendships raw data:', friendships)

# Check users
cursor.execute("SELECT id, username FROM users")
users = cursor.fetchall()
print('Users:', users)

# Check specific friendship details
cursor.execute("""
    SELECT f.id, u1.username as sender, u2.username as receiver, f.status, f.created_at
    FROM friendships f
    JOIN users u1 ON f.user_id = u1.id
    JOIN users u2 ON f.friend_id = u2.id
""")
detailed_friendships = cursor.fetchall()
print('Detailed friendships:', detailed_friendships)

conn.close()
