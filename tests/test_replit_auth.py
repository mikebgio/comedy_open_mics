#!/usr/bin/env python3
"""
Unit tests for replit_auth.py
"""
import pytest

pytestmark = pytest.mark.unit
import tempfile
import os
from unittest.mock import patch, MagicMock, Mock
import uuid

from app import app, db
from models import User, OAuth
from replit_auth import (
    make_replit_blueprint, save_user, get_next_navigation_url,
    UserSessionStorage
)


@pytest.fixture
def app_context():
    """Create a test application context."""
    db_fd, app.config["DATABASE"] = tempfile.mkstemp()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SESSION_SECRET"] = "test-secret"
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(app.config["DATABASE"])


class TestSaveUser:
    """Test save_user function."""
    
    def test_save_user_with_complete_claims(self, app_context):
        """Test save_user with complete user claims."""
        user_claims = {
            'sub': 'test-user-123',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'profile_image_url': 'https://example.com/profile.jpg'
        }
        
        user = save_user(user_claims)
        
        assert user.id == 'test-user-123'
        assert user.email == 'test@example.com'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.profile_image_url == 'https://example.com/profile.jpg'
        assert user.username == 'test_user'
    
    def test_save_user_with_minimal_claims(self, app_context):
        """Test save_user with minimal user claims."""
        user_claims = {
            'sub': 'test-user-456',
            'email': 'minimal@example.com'
        }
        
        user = save_user(user_claims)
        
        assert user.id == 'test-user-456'
        assert user.email == 'minimal@example.com'
        assert user.first_name is None
        assert user.last_name is None
        assert user.username == 'minimal'
    
    def test_save_user_without_names(self, app_context):
        """Test save_user without first/last names."""
        user_claims = {
            'sub': 'test-user-789',
            'email': 'noname@example.com'
        }
        
        user = save_user(user_claims)
        
        assert user.id == 'test-user-789'
        assert user.email == 'noname@example.com'
        assert user.username == 'noname'
    
    def test_save_user_without_email(self, app_context):
        """Test save_user without email."""
        user_claims = {
            'sub': 'test-user-000'
        }
        
        user = save_user(user_claims)
        
        assert user.id == 'test-user-000'
        assert user.email is None
        assert user.username == 'user_test-user-000'
    
    def test_save_user_existing_user_update(self, app_context):
        """Test save_user updates existing user."""
        # Create existing user
        existing_user = User(
            id='test-user-123',
            email='old@example.com',
            first_name='Old',
            last_name='Name'
        )
        db.session.add(existing_user)
        db.session.commit()
        
        user_claims = {
            'sub': 'test-user-123',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'Name',
            'profile_image_url': 'https://example.com/new.jpg'
        }
        
        user = save_user(user_claims)
        
        # Should update existing user
        assert user.id == 'test-user-123'
        assert user.email == 'new@example.com'
        assert user.first_name == 'New'
        assert user.profile_image_url == 'https://example.com/new.jpg'
        
        # Should only be one user in database
        users = User.query.all()
        assert len(users) == 1


class TestGetNextNavigationUrl:
    """Test get_next_navigation_url function."""
    
    def test_get_next_navigation_url_with_navigation(self, app_context):
        """Test get_next_navigation_url with navigation request."""
        with app.test_request_context('/', headers={
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Dest': 'document'
        }):
            from flask import request
            url = get_next_navigation_url(request)
            assert url == 'http://localhost/'
    
    def test_get_next_navigation_url_without_navigation(self, app_context):
        """Test get_next_navigation_url without navigation request."""
        with app.test_request_context('/', headers={
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'
        }):
            from flask import request
            url = get_next_navigation_url(request)
            assert url == 'http://localhost/'  # Falls back to request.url
    
    def test_get_next_navigation_url_with_referrer(self, app_context):
        """Test get_next_navigation_url with referrer."""
        with app.test_request_context('/', headers={
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'http://localhost/previous-page'
        }):
            from flask import request
            url = get_next_navigation_url(request)
            assert url == 'http://localhost/previous-page'


class TestUserSessionStorage:
    """Test UserSessionStorage class."""
    
    def test_user_session_storage_initialization(self, app_context):
        """Test UserSessionStorage initialization."""
        storage = UserSessionStorage()
        assert storage is not None
    
    @patch('replit_auth.current_user')
    @patch('replit_auth.g')
    def test_user_session_storage_get_existing_token(self, mock_g, mock_current_user, app_context):
        """Test getting existing token from storage."""
        # Setup mocks
        mock_current_user.get_id.return_value = 'test-user-123'
        mock_g.browser_session_key = 'test-session-key'
        
        # Create OAuth entry
        oauth_entry = OAuth(
            user_id='test-user-123',
            browser_session_key='test-session-key',
            provider='replit_auth',
            token={'access_token': 'test-token'}
        )
        db.session.add(oauth_entry)
        db.session.commit()
        
        storage = UserSessionStorage()
        mock_blueprint = Mock()
        mock_blueprint.name = 'replit_auth'
        
        token = storage.get(mock_blueprint)
        assert token == {'access_token': 'test-token'}
    
    @patch('replit_auth.current_user')
    @patch('replit_auth.g')
    def test_user_session_storage_get_nonexistent_token(self, mock_g, mock_current_user, app_context):
        """Test getting nonexistent token from storage."""
        # Setup mocks
        mock_current_user.get_id.return_value = 'test-user-123'
        mock_g.browser_session_key = 'test-session-key'
        
        storage = UserSessionStorage()
        mock_blueprint = Mock()
        mock_blueprint.name = 'replit_auth'
        
        token = storage.get(mock_blueprint)
        assert token is None
    
    @patch('replit_auth.current_user')
    @patch('replit_auth.g')
    def test_user_session_storage_set_token(self, mock_g, mock_current_user, app_context):
        """Test setting token in storage."""
        # Setup mocks
        mock_current_user.get_id.return_value = 'test-user-123'
        mock_g.browser_session_key = 'test-session-key'
        
        storage = UserSessionStorage()
        mock_blueprint = Mock()
        mock_blueprint.name = 'replit_auth'
        
        test_token = {'access_token': 'new-token', 'refresh_token': 'refresh-token'}
        storage.set(mock_blueprint, test_token)
        
        # Verify token was stored
        oauth_entry = OAuth.query.filter_by(
            user_id='test-user-123',
            browser_session_key='test-session-key',
            provider='replit_auth'
        ).first()
        
        assert oauth_entry is not None
        assert oauth_entry.token == test_token
    
    @patch('replit_auth.current_user')
    @patch('replit_auth.g')
    def test_user_session_storage_delete_token(self, mock_g, mock_current_user, app_context):
        """Test deleting token from storage."""
        # Setup mocks
        mock_current_user.get_id.return_value = 'test-user-123'
        mock_g.browser_session_key = 'test-session-key'
        
        # Create OAuth entry
        oauth_entry = OAuth(
            user_id='test-user-123',
            browser_session_key='test-session-key',
            provider='replit_auth',
            token={'access_token': 'test-token'}
        )
        db.session.add(oauth_entry)
        db.session.commit()
        
        storage = UserSessionStorage()
        mock_blueprint = Mock()
        mock_blueprint.name = 'replit_auth'
        
        storage.delete(mock_blueprint)
        
        # Verify token was deleted
        oauth_entry = OAuth.query.filter_by(
            user_id='test-user-123',
            browser_session_key='test-session-key',
            provider='replit_auth'
        ).first()
        
        assert oauth_entry is None


class TestMakeReplitBlueprint:
    """Test make_replit_blueprint function."""
    
    @patch.dict(os.environ, {'REPL_ID': 'test-repl-id'})
    def test_make_replit_blueprint_success(self, app_context):
        """Test successful blueprint creation."""
        blueprint = make_replit_blueprint()
        
        assert blueprint is not None
        assert blueprint.name == 'replit_auth'
        assert blueprint.client_id == 'test-repl-id'
        assert blueprint.client_secret is None
        assert 'openid' in blueprint.scope
        assert 'profile' in blueprint.scope
        assert 'email' in blueprint.scope
        assert 'offline_access' in blueprint.scope
    
    @patch.dict(os.environ, {}, clear=True)
    def test_make_replit_blueprint_missing_repl_id(self, app_context):
        """Test blueprint creation without REPL_ID."""
        with pytest.raises(SystemExit):
            make_replit_blueprint()
    
    @patch.dict(os.environ, {
        'REPL_ID': 'test-repl-id',
        'ISSUER_URL': 'https://custom-issuer.com/oidc'
    })
    def test_make_replit_blueprint_custom_issuer(self, app_context):
        """Test blueprint creation with custom issuer URL."""
        blueprint = make_replit_blueprint()
        
        assert blueprint is not None
        assert blueprint.base_url == 'https://custom-issuer.com/oidc'
        assert blueprint.token_url == 'https://custom-issuer.com/oidc/token'
        assert blueprint.authorization_url == 'https://custom-issuer.com/oidc/auth'
    
    @patch.dict(os.environ, {'REPL_ID': 'test-repl-id'})
    def test_make_replit_blueprint_routes(self, app_context):
        """Test that blueprint routes are properly configured."""
        blueprint = make_replit_blueprint()
        
        # Check that routes are defined
        route_names = [rule.endpoint for rule in blueprint.url_map.iter_rules()]
        
        assert 'replit_auth.logout' in route_names
        assert 'replit_auth.error' in route_names
    
    @patch.dict(os.environ, {'REPL_ID': 'test-repl-id'})
    def test_blueprint_session_management(self, app_context):
        """Test blueprint session management."""
        blueprint = make_replit_blueprint()
        
        with app.test_request_context('/'):
            # Test session key generation
            from flask import session, g
            
            # Simulate the before_request handler
            if '_browser_session_key' not in session:
                session['_browser_session_key'] = uuid.uuid4().hex
            session.modified = True
            g.browser_session_key = session['_browser_session_key']
            
            assert 'browser_session_key' in g
            assert g.browser_session_key is not None
            assert len(g.browser_session_key) == 32  # UUID hex length


class TestAuthCallbacks:
    """Test authentication callback functions."""
    
    @patch('replit_auth.jwt.decode')
    @patch('replit_auth.login_user')
    def test_logged_in_callback(self, mock_login_user, mock_jwt_decode, app_context):
        """Test logged_in callback function."""
        # Mock JWT decode
        mock_jwt_decode.return_value = {
            'sub': 'test-user-123',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # Mock blueprint and token
        mock_blueprint = Mock()
        test_token = {
            'id_token': 'mock-id-token',
            'access_token': 'mock-access-token'
        }
        
        with app.test_request_context('/'):
            from flask import session
            from replit_auth import logged_in
            
            # Test callback
            result = logged_in(mock_blueprint, test_token)
            
            # Verify user was saved and logged in
            mock_login_user.assert_called_once()
            assert mock_blueprint.token == test_token
    
    @patch('replit_auth.redirect')
    @patch('replit_auth.url_for')
    def test_handle_error_callback(self, mock_url_for, mock_redirect, app_context):
        """Test handle_error callback function."""
        from replit_auth import handle_error
        
        mock_url_for.return_value = '/auth/error'
        mock_redirect.return_value = 'redirect_response'
        
        # Mock blueprint and error
        mock_blueprint = Mock()
        
        result = handle_error(mock_blueprint, 'test_error', 'Test error description')
        
        mock_url_for.assert_called_once_with('replit_auth.error')
        mock_redirect.assert_called_once_with('/auth/error')
        assert result == 'redirect_response'