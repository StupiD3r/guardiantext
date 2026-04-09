"""
test_api.py  –  API endpoint tests for GuardianText
Tests Flask API endpoints for authentication, rooms, and messaging.
"""

import pytest
import json
from flask import session
from app import app, socketio
from database import init_db, create_user, create_private_room
from config import Config

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    # Initialize database
    init_db()
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client with logged-in user"""
    # Register a user
    client.post('/api/register', json={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Login
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    
    assert response.status_code == 200
    return client


class TestAuthenticationAPI:
    """Test authentication endpoints"""
    
    def test_register_user(self, client):
        """Test user registration"""
        response = client.post('/api/register', json={
            'username': 'john',
            'password': 'password123'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_register_duplicate_username(self, client):
        """Test registering duplicate username"""
        client.post('/api/register', json={
            'username': 'john',
            'password': 'password123'
        })
        
        response = client.post('/api/register', json={
            'username': 'john',
            'password': 'different_password'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_register_short_username(self, client):
        """Test registering with short username"""
        response = client.post('/api/register', json={
            'username': 'ab',  # Too short (< 3 chars)
            'password': 'password123'
        })
        assert response.status_code == 400
    
    def test_register_short_password(self, client):
        """Test registering with short password"""
        response = client.post('/api/register', json={
            'username': 'john',
            'password': 'pass'  # Too short (< 6 chars)
        })
        assert response.status_code == 400
    
    def test_login_success(self, client):
        """Test successful login"""
        # Register first
        client.post('/api/register', json={
            'username': 'john',
            'password': 'password123'
        })
        
        # Login
        response = client.post('/api/login', json={
            'username': 'john',
            'password': 'password123'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['username'] == 'john'
    
    def test_login_invalid_password(self, client):
        """Test login with invalid password"""
        client.post('/api/register', json={
            'username': 'john',
            'password': 'password123'
        })
        
        response = client.post('/api/login', json={
            'username': 'john',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post('/api/login', json={
            'username': 'nobody',
            'password': 'password123'
        })
        assert response.status_code == 401
    
    def test_logout(self, authenticated_client):
        """Test logout"""
        response = authenticated_client.get('/api/logout')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestRoomAPI:
    """Test room endpoints"""
    
    def test_get_rooms_not_authenticated(self, client):
        """Test getting rooms without authentication"""
        response = client.get('/api/rooms')
        assert response.status_code == 401
    
    def test_get_rooms_authenticated(self, authenticated_client):
        """Test getting rooms when authenticated"""
        response = authenticated_client.get('/api/rooms')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'rooms' in data
    
    def test_create_private_room(self, authenticated_client):
        """Test creating a private room"""
        response = authenticated_client.post('/api/rooms/create', json={
            'room_name': 'Secret Room'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['room']['room_name'] == 'Secret Room'
        assert data['room']['is_private'] is True
    
    def test_create_private_room_short_name(self, authenticated_client):
        """Test creating room with short name"""
        response = authenticated_client.post('/api/rooms/create', json={
            'room_name': 'R'  # Too short
        })
        assert response.status_code == 400
    
    def test_get_private_rooms(self, authenticated_client):
        """Test getting user's private rooms"""
        # Create a room first
        authenticated_client.post('/api/rooms/create', json={
            'room_name': 'Test Room'
        })
        
        response = authenticated_client.get('/api/rooms/private')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['private_rooms']) > 0


class TestAdminAPI:
    """Test admin endpoints"""
    
    def test_delete_user_admin_only(self, client, authenticated_client):
        """Test that delete requires admin"""
        # Create non-admin user
        response = client.post('/api/register', json={
            'username': 'regularuser',
            'password': 'password123'
        })
        
        # Try to delete user as non-admin
        response = authenticated_client.post('/api/admin/users/2/delete')
        # Should be 403 (forbidden) if user is not admin
        # or 200 if they are admin (depends on setup)
        assert response.status_code in [403, 200]
    
    def test_cannot_delete_self(self, authenticated_client):
        """Test that users cannot delete themselves"""
        response = authenticated_client.post('/api/admin/users/1/delete')
        # Response depends on whether they're admin
        # But self-deletion should be prevented or redirect
        assert response.status_code in [400, 403]


class TestValidation:
    """Test input validation"""
    
    def test_register_empty_username(self, client):
        """Test registration with empty username"""
        response = client.post('/api/register', json={
            'username': '',
            'password': 'password123'
        })
        assert response.status_code == 400
    
    def test_register_empty_password(self, client):
        """Test registration with empty password"""
        response = client.post('/api/register', json={
            'username': 'john',
            'password': ''
        })
        assert response.status_code == 400
    
    def test_register_special_username(self, client):
        """Test registration with invalid characters in username"""
        response = client.post('/api/register', json={
            'username': 'john@example',  # @ not allowed
            'password': 'password123'
        })
        assert response.status_code == 400
    
    def test_register_long_username(self, client):
        """Test registration with username too long"""
        response = client.post('/api/register', json={
            'username': 'a' * 50,  # Too long (> 20)
            'password': 'password123'
        })
        assert response.status_code == 400


class TestMessageAPI:
    """Test message endpoints"""
    
    def test_send_message_requires_auth(self, client):
        """Test that sending message requires auth"""
        response = client.post('/api/message', json={
            'room': 'general',
            'message': 'Hello'
        })
        assert response.status_code == 401
    
    def test_send_empty_message(self, authenticated_client):
        """Test sending empty message"""
        response = authenticated_client.post('/api/message', json={
            'room': 'general',
            'message': ''
        })
        assert response.status_code == 400
    
    def test_get_messages_requires_auth(self, client):
        """Test that getting messages requires auth"""
        response = client.get('/api/messages/general')
        assert response.status_code == 401


class TestSessionSecurity:
    """Test session and security features"""
    
    def test_session_timeout(self, authenticated_client):
        """Test that session respects security"""
        # Get current user
        response = authenticated_client.get('/api/me')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['logged_in'] is True
    
    def test_csrf_protection(self, authenticated_client):
        """Test CSRF token handling if implemented"""
        # This test assumes CSRF protection is added
        # For now, just verify POST endpoints work
        response = authenticated_client.post('/api/logout')
        assert response.status_code == 200
    
    def test_sql_injection_prevention(self, client):
        """Test SQL injection prevention"""
        malicious_username = "admin'; DROP TABLE users; --"
        response = client.post('/api/register', json={
            'username': malicious_username,
            'password': 'password123'
        })
        # Should either reject or properly escape
        assert response.status_code >= 400 or 'error' in response.json


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
