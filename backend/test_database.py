"""
test_database.py  –  Database function tests for GuardianText
Tests core database operations including user management, rooms, and messaging.
"""

import pytest
import sqlite3
import os
import sys
import tempfile
import shutil
from database import (
    init_db, create_user, verify_user, get_user_by_id,
    delete_user, verify_password, hash_password,
    create_private_room, get_user_private_rooms,
    invite_friend_to_room, accept_room_invitation, get_room_invitations,
    save_message, get_room_messages, get_db
)
from config import Config

# Store original DB path
original_db_path = Config.DATABASE_PATH

@pytest.fixture(scope='function', autouse=True)
def isolated_db():
    """Create isolated database for each test"""
    # Create temporary directory and database file
    test_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(test_dir, 'test.db')
    
    # Override config
    Config.DATABASE_PATH = test_db_path
    
    # Initialize database
    init_db()
    
    yield
    
    # Cleanup
    Config.DATABASE_PATH = original_db_path
    try:
        shutil.rmtree(test_dir)
    except:
        pass

class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a hash"""
        password = "test123"
        hashed = hash_password(password)
        assert hashed is not None
        assert hashed != password  # Hash should differ from plaintext
        assert len(hashed) > 10  # bcrypt hashes are long
    
    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = "test123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = "test123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False
    
    def test_hash_different_for_same_password(self):
        """Test that hashing same password produces different hashes (due to salt)"""
        password = "test123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts = different hashes
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestUserCreation:
    """Test user creation and verification"""
    
    def test_create_user_success(self):
        """Test creating a new user"""
        success, msg = create_user("john", "password123")
        assert success is True
        assert msg == "Account created successfully."
    
    def test_create_user_duplicate_username(self):
        """Test that duplicate usernames are rejected"""
        create_user("john", "password123")
        success, msg = create_user("john", "different_password")
        assert success is False
        assert "already taken" in msg
    
    def test_create_user_stores_hashed_password(self):
        """Test that password is stored as hash, not plaintext"""
        create_user("john", "password123")
        conn = get_db()
        row = conn.execute("SELECT password_hash FROM users WHERE username=?", ("john",)).fetchone()
        conn.close()
        
        assert row is not None
        password_hash = row['password_hash']
        assert password_hash != "password123"  # Should not be plaintext
        assert verify_password("password123", password_hash) is True


class TestUserVerification:
    """Test user login verification"""
    
    def test_verify_user_correct_password(self):
        """Test verifying user with correct password"""
        create_user("john", "password123")
        success, user = verify_user("john", "password123")
        assert success is True
        assert user['username'] == "john"
        assert user['id'] == 1
    
    def test_verify_user_wrong_password(self):
        """Test verifying user with wrong password"""
        create_user("john", "password123")
        success, user = verify_user("john", "wrongpassword")
        assert success is False
        assert user is None
    
    def test_verify_user_nonexistent(self):
        """Test verifying non-existent user"""
        success, user = verify_user("nonexistent", "password123")
        assert success is False
        assert user is None


class TestUserRetrieval:
    """Test getting user by ID"""
    
    def test_get_user_by_id(self):
        """Test retrieving user by ID"""
        create_user("john", "password123")
        user = get_user_by_id(1)
        assert user is not None
        assert user['username'] == "john"
        assert user['id'] == 1
    
    def test_get_user_by_id_nonexistent(self):
        """Test retrieving non-existent user"""
        user = get_user_by_id(999)
        assert user is None


class TestUserDeletion:
    """Test user deletion and cascading deletes"""
    
    def test_delete_user_success(self):
        """Test deleting a user"""
        create_user("john", "password123")
        delete_user(1)
        user = get_user_by_id(1)
        assert user is None
    
    def test_delete_user_cascades_messages(self):
        """Test that deleting user deletes their messages"""
        create_user("john", "password123")
        save_message("general", 1, "Hello", 0.1)  # user_id=1
        
        delete_user(1)
        
        messages = get_room_messages("general", limit=100)
        assert len(messages) == 0
    
    def test_delete_user_cascades_rooms(self):
        """Test that deleting user deletes their owned rooms"""
        create_user("john", "password123")
        success, msg, room_id = create_private_room("My Room", owner_id=1)
        
        # Verify room exists
        rooms = get_user_private_rooms(1)
        assert len(rooms) == 1
        
        # Delete user
        delete_user(1)
        
        # Verify room is gone
        rooms = get_user_private_rooms(1)
        assert len(rooms) == 0


class TestPrivateRooms:
    """Test private room functionality"""
    
    def test_create_private_room(self):
        """Test creating a private room"""
        create_user("john", "password123")
        success, msg, room_id = create_private_room("Test Room", owner_id=1)
        assert success is True
        assert room_id is not None
    
    def test_get_user_private_rooms(self):
        """Test retrieving user's private rooms"""
        create_user("john", "password123")
        create_private_room("Room 1", owner_id=1)
        create_private_room("Room 2", owner_id=1)
        
        rooms = get_user_private_rooms(1)
        assert len(rooms) == 2
        room_names = [r['name'] for r in rooms]
        assert "Room 1" in room_names
        assert "Room 2" in room_names
    
    def test_get_private_rooms_empty(self):
        """Test getting private rooms when none exist"""
        create_user("john", "password123")
        rooms = get_user_private_rooms(1)
        assert len(rooms) == 0


class TestFriendInvitations:
    """Test friend invitations to rooms"""
    
    def test_invite_friend_to_room(self):
        """Test inviting a friend to a room"""
        create_user("john", "password123")
        create_user("jane", "password123")
        success, msg, room_id = create_private_room("Test Room", owner_id=1)
        
        success, msg = invite_friend_to_room(room_id, friend_id=2, inviter_id=1)
        assert success is True
    
    def test_accept_room_invitation(self):
        """Test accepting a room invitation"""
        create_user("john", "password123")
        create_user("jane", "password123")
        success, msg, room_id = create_private_room("Test Room", owner_id=1)
        success, msg = invite_friend_to_room(room_id, friend_id=2, inviter_id=1)
        
        # Get the invitation ID
        invitations = get_room_invitations(2)
        if invitations:
            result, msg = accept_room_invitation(invitations[0]['id'], user_id=2)
            assert result is True


class TestMessaging:
    """Test message saving and retrieval"""
    
    def test_save_message(self):
        """Test saving a message"""
        create_user("john", "password123")
        save_message(sender_id=1, sender_username="john", room="general", 
                    content="Hello world", toxicity_score=0.1)
        messages = get_room_messages("general", limit=100)
        assert len(messages) >= 1
    
    def test_get_room_messages(self):
        """Test retrieving messages from a room"""
        create_user("john", "password123")
        save_message(sender_id=1, sender_username="john", room="general", 
                    content="Message 1", toxicity_score=0.1)
        save_message(sender_id=1, sender_username="john", room="general", 
                    content="Message 2", toxicity_score=0.2)
        
        messages = get_room_messages("general", limit=100)
        assert len(messages) >= 2
    
    def test_get_room_messages_limit(self):
        """Test message limit in get_room_messages"""
        create_user("john", "password123")
        for i in range(10):
            save_message(sender_id=1, sender_username="john", room="general", 
                        content=f"Message {i}", toxicity_score=0.1)
        
        messages = get_room_messages("general", limit=5)
        assert len(messages) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
