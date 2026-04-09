#!/usr/bin/env python3
"""Debug admin login issue."""

from database import get_db, hash_password, verify_password

conn = get_db()
cur = conn.cursor()

# Check if admin user exists
cur.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username='admin'")
admin = cur.fetchone()

if admin:
    print(f"Admin user found:")
    print(f"  ID: {admin['id']}")
    print(f"  Username: {admin['username']}")
    print(f"  Is Admin: {admin['is_admin']}")
    print(f"  Password Hash: {admin['password_hash'][:50]}...")
    
    # Test password verification
    test_password = "admin123"
    is_valid = verify_password(test_password, admin['password_hash'])
    print(f"\nPassword verification for '{test_password}': {is_valid}")
    
    if not is_valid:
        print("\n❌ Password hash mismatch! Likely from old SHA256 system.")
        print("Rehashing with bcrypt...")
        new_hash = hash_password(test_password)
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, admin['id']))
        conn.commit()
        print("✅ Password updated with bcrypt hash!")
else:
    print("❌ Admin user not found in database!")
    print("Creating default admin user...")
    from database import ensure_default_admin
    ensure_default_admin()
    print("✅ Admin user created!")

conn.close()
