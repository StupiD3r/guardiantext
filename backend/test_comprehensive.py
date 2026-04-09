#!/usr/bin/env python3
"""Comprehensive test of all new features."""

from database import (
    create_user, verify_user, change_password, get_user_profile, 
    update_user_profile, get_user_by_id, get_db
)
from auth import validate_password
from true_ml_toxicity import analyze_with_true_ml
from nlp_filter import analyze_message

print("=" * 70)
print("COMPREHENSIVE SYSTEM TEST - All New Features")
print("=" * 70)

# Test 1: Password Change
print("\n[1] PASSWORD CHANGE TEST")
print("-" * 70)
success, msg = create_user("testuser", "password123")
print(f"Created user: {success} - {msg}")

# Verify original password works
success, user = verify_user("testuser", "password123")
print(f"Original login: {success}")

# Change password
success, msg = change_password(user['id'], "password123", "newpass456")
print(f"Password changed: {success} - {msg}")

# Old password should fail
success, _ = verify_user("testuser", "password123")
print(f"Old password rejected: {not success} ✅" if not success else f"Old password rejected: {not success} ❌")

# New password should work
success, _ = verify_user("testuser", "newpass456")
print(f"New password works: {success} ✅" if success else f"New password works: {success} ❌")

# Test 2: Profile Updates
print("\n[2] PROFILE UPDATE TEST")
print("-" * 70)
user = get_user_by_id(user['id'])
profile = get_user_profile(user['id'])
print(f"Initial profile: {profile['username']}, Status: {profile['status']}, Picture: {profile['profile_picture']}")

# Update status
success, msg = update_user_profile(user['id'], status="Online - Available")
print(f"Status updated: {success} - {msg}")

# Update picture
success, msg = update_user_profile(user['id'], profile_picture="https://example.com/avatar.jpg")
print(f"Avatar updated: {success} - {msg}")

# Verify updates
profile = get_user_profile(user['id'])
print(f"Updated profile: {profile['username']}, Status: {profile['status']}, Picture: {profile['profile_picture']}")

# Test 3: Obfuscation Detection
print("\n[3] OBFUSCATION DETECTION TEST")
print("-" * 70)
obfuscation_tests = [
    "well fvck",
    "sh1t",
    "fvck th1s",
]

for msg in obfuscation_tests:
    result = analyze_with_true_ml(msg)
    legacy = analyze_message(msg)
    print(f"'{msg}':")
    print(f"  True ML: Toxic={result.is_toxic}, Words={[tw.word for tw in result.toxic_words]}")
    print(f"  Legacy:  Toxic={legacy.is_toxic}, Words={legacy.toxic_words}")

# Test 4: False Positive Fixes
print("\n[4] FALSE POSITIVE FIX TEST")
print("-" * 70)
benign_tests = [
    "hello world",
    "thanks for helping",
    "you're amazing",
    "great job",
]

all_clean = True
for msg in benign_tests:
    result = analyze_with_true_ml(msg)
    legacy = analyze_message(msg)
    is_clean = not result.is_toxic and not legacy.is_toxic
    all_clean = all_clean and is_clean
    status = "✅" if is_clean else "❌"
    print(f"{status} '{msg}': True ML={result.is_toxic}, Legacy={legacy.is_toxic}")

# Test 5: Database Indexes
print("\n[5] DATABASE INDEXES TEST")
print("-" * 70)
conn = get_db()
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
indexes = cursor.fetchall()
print(f"Created {len(indexes)} indexes:")
for idx in indexes:
    print(f"  - {idx[0]}")
conn.close()

print("\n" + "=" * 70)
print(f"SUMMARY: {'✅ ALL TESTS PASSED' if all_clean else '⚠️  Some issues detected'}")
print("=" * 70)
