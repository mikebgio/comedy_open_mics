#!/usr/bin/env python3
"""
Unit tests for routes.py
"""
import pytest

pytestmark = pytest.mark.unit
import tempfile
import os
from datetime import date, time
from unittest.mock import patch, MagicMock

from app import app, db
from models import User, Show, ShowInstance, Signup
from routes import is_safe_url


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


@pytest.fixture
def client(app_context):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    user = User(
        id="test-user-123",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        username="testuser"
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_show(sample_user):
    """Create a sample show for testing."""
    show = Show(
        name="Test Comedy Show",
        venue="Test Venue",
        address="123 Comedy St, Boston, MA",
        timezone="America/New_York",
        day_of_week="Monday",
        start_time=time(19, 0),
        end_time=time(21, 0),
        max_signups=10,
        owner_id=sample_user.id,
        default_host_id=sample_user.id
    )
    db.session.add(show)
    db.session.commit()
    return show


class TestUtilityFunctions:
    """Test utility functions in routes.py."""
    
    def test_is_safe_url_safe(self, client):
        """Test is_safe_url with safe URLs."""
        with app.test_request_context('http://localhost/'):
            assert is_safe_url('http://localhost/dashboard') is True
            assert is_safe_url('/dashboard') is True
            assert is_safe_url('https://localhost/events') is True
    
    def test_is_safe_url_unsafe(self, client):
        """Test is_safe_url with unsafe URLs."""
        with app.test_request_context('http://localhost/'):
            assert is_safe_url('http://evil.com/hack') is False
            assert is_safe_url('https://malicious.site/') is False
            assert is_safe_url('ftp://localhost/file') is False
    
    def test_is_safe_url_edge_cases(self, client):
        """Test is_safe_url with edge cases."""
        with app.test_request_context('http://localhost/'):
            assert is_safe_url('') is True  # Empty string
            assert is_safe_url('javascript:alert("xss")') is False
            assert is_safe_url('//evil.com/hack') is False


class TestIndexRoute:
    """Test index route functionality."""
    
    def test_index_route_anonymous(self, client):
        """Test index route for anonymous users."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Login with Replit' in response.data
        assert b'Comedy Open Mic Manager' in response.data
    
    @patch('routes.current_user')
    def test_index_route_authenticated(self, mock_current_user, client, sample_user):
        """Test index route for authenticated users."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = sample_user.id
        mock_current_user.owned_shows = []
        mock_current_user.show_runner_roles = []
        mock_current_user.show_host_roles = []
        
        response = client.get('/')
        assert response.status_code == 200


class TestAPIRoutes:
    """Test API routes functionality."""
    
    @patch('routes.current_user')
    def test_get_show_data_unauthorized(self, mock_current_user, client, sample_show):
        """Test get_show_data without permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_edit_show.return_value = False
        
        response = client.get(f'/api/show/{sample_show.id}')
        assert response.status_code == 403
    
    @patch('routes.current_user')
    def test_get_show_data_authorized(self, mock_current_user, client, sample_show):
        """Test get_show_data with permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_edit_show.return_value = True
        
        response = client.get(f'/api/show/{sample_show.id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['name'] == 'Test Comedy Show'
        assert data['venue'] == 'Test Venue'
        assert data['day_of_week'] == 'Monday'
    
    @patch('routes.current_user')
    def test_create_show_api_missing_fields(self, mock_current_user, client):
        """Test create_show_api with missing required fields."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test-user-123"
        
        response = client.post('/api/show', json={
            'name': 'Test Show'
            # Missing other required fields
        })
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'error' in data
        assert 'Missing required field' in data['error']
    
    @patch('routes.current_user')
    def test_create_show_api_valid_data(self, mock_current_user, client):
        """Test create_show_api with valid data."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test-user-123"
        
        show_data = {
            'name': 'New Comedy Show',
            'venue': 'New Venue',
            'address': '456 Comedy Ave, Boston, MA',
            'day_of_week': 'Wednesday',
            'start_time': '20:00',
            'end_time': '22:00',
            'max_signups': 15,
            'signups_open_value': 3,
            'signups_open_unit': 'days',
            'signups_closed_value': 30,
            'signups_closed_unit': 'minutes',
            'signup_deadline_hours': 1,
            'timezone': 'America/New_York',
            'description': 'A new comedy show',
            'show_host_info': True,
            'show_owner_info': False
        }
        
        response = client.post('/api/show', json=show_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'show_id' in data
        
        # Verify show was created
        show = Show.query.filter_by(name='New Comedy Show').first()
        assert show is not None
        assert show.venue == 'New Venue'
        assert show.max_signups == 15


class TestEventRoutes:
    """Test event-related routes."""
    
    @patch('routes.current_user')
    def test_event_info_route(self, mock_current_user, client, sample_show):
        """Test event_info route."""
        # Create a show instance
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        response = client.get(f'/event/{instance.id}')
        assert response.status_code == 200
        assert b'Test Comedy Show' in response.data
    
    @patch('routes.current_user')
    def test_signup_for_event_unauthorized(self, mock_current_user, client, sample_show):
        """Test signup_for_event without authentication."""
        mock_current_user.is_authenticated = False
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        response = client.get(f'/event/{instance.id}/signup')
        assert response.status_code == 302  # Redirect to login
    
    @patch('routes.current_user')
    def test_cancel_signup_unauthorized(self, mock_current_user, client, sample_show, sample_user):
        """Test cancel_signup without proper permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "different-user"
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        signup = Signup(
            comedian_id=sample_user.id,
            show_instance_id=instance.id
        )
        db.session.add(signup)
        db.session.commit()
        
        response = client.post(f'/cancel_signup/{signup.id}')
        assert response.status_code == 403


class TestHostRoutes:
    """Test host-specific routes."""
    
    @patch('routes.current_user')
    def test_host_dashboard_route(self, mock_current_user, client, sample_user):
        """Test host_dashboard route."""
        mock_current_user.is_authenticated = True
        mock_current_user.owned_shows = []
        mock_current_user.show_runner_roles = []
        mock_current_user.show_host_roles = []
        
        response = client.get('/host/dashboard')
        assert response.status_code == 200
        assert b'Manage Shows' in response.data
    
    @patch('routes.current_user')
    def test_upcoming_lineups_unauthorized(self, mock_current_user, client, sample_show):
        """Test upcoming_lineups without permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = False
        
        response = client.get(f'/host/upcoming_lineups/{sample_show.id}')
        assert response.status_code == 302  # Redirect
    
    @patch('routes.current_user')
    def test_upcoming_lineups_authorized(self, mock_current_user, client, sample_show):
        """Test upcoming_lineups with permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = True
        
        response = client.get(f'/host/upcoming_lineups/{sample_show.id}')
        assert response.status_code == 200
        assert b'Test Comedy Show' in response.data
    
    @patch('routes.current_user')
    def test_cancel_show_instance_unauthorized(self, mock_current_user, client, sample_show):
        """Test cancel_show_instance without permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = False
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        response = client.post(f'/cancel_show_instance/{instance.id}')
        assert response.status_code == 403
    
    @patch('routes.current_user')
    def test_cancel_show_instance_authorized(self, mock_current_user, client, sample_show):
        """Test cancel_show_instance with permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = True
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        response = client.post(f'/cancel_show_instance/{instance.id}', json={
            'reason': 'Test cancellation'
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        
        # Verify instance was cancelled
        instance = ShowInstance.query.get(instance.id)
        assert instance.is_cancelled is True
        assert instance.cancellation_reason == 'Test cancellation'


class TestComediianRoutes:
    """Test comedian-specific routes."""
    
    @patch('routes.current_user')
    def test_comedian_dashboard_route(self, mock_current_user, client, sample_user):
        """Test comedian_dashboard route."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = sample_user.id
        
        response = client.get('/comedian/dashboard')
        assert response.status_code == 200
        assert b'Find Shows' in response.data
    
    @patch('routes.current_user')
    def test_calendar_view_route(self, mock_current_user, client, sample_user):
        """Test calendar_view route."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = sample_user.id
        
        response = client.get('/calendar')
        assert response.status_code == 200
        assert b'Calendar' in response.data
    
    @patch('routes.current_user')
    def test_calendar_events_api(self, mock_current_user, client, sample_show):
        """Test calendar_events_api route."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test-user-123"
        
        # Create some show instances
        instance1 = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        instance2 = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 22)
        )
        db.session.add_all([instance1, instance2])
        db.session.commit()
        
        response = client.get('/api/calendar/events')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data) >= 2
        assert any(event['title'] == 'Test Comedy Show' for event in data)


class TestLineupManagement:
    """Test lineup management routes."""
    
    @patch('routes.current_user')
    def test_manage_lineup_unauthorized(self, mock_current_user, client, sample_show):
        """Test manage_lineup without permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = False
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        response = client.get(f'/manage_lineup/{instance.id}')
        assert response.status_code == 302  # Redirect
    
    @patch('routes.current_user')
    def test_manage_lineup_authorized(self, mock_current_user, client, sample_show):
        """Test manage_lineup with permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = True
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        response = client.get(f'/manage_lineup/{instance.id}')
        assert response.status_code == 200
        assert b'Manage Lineup' in response.data
    
    @patch('routes.current_user')
    def test_reorder_lineup_unauthorized(self, mock_current_user, client, sample_show):
        """Test reorder_lineup without permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = False
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        response = client.post(f'/reorder_lineup/{instance.id}', json={
            'signup_ids': [1, 2, 3]
        })
        assert response.status_code == 403
    
    @patch('routes.current_user')
    def test_reorder_lineup_authorized(self, mock_current_user, client, sample_show, sample_user):
        """Test reorder_lineup with permission."""
        mock_current_user.is_authenticated = True
        mock_current_user.can_manage_lineup.return_value = True
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        # Create signups
        signup1 = Signup(
            comedian_id=sample_user.id,
            show_instance_id=instance.id,
            position=1
        )
        signup2 = Signup(
            comedian_id=sample_user.id,
            show_instance_id=instance.id,
            position=2
        )
        db.session.add_all([signup1, signup2])
        db.session.commit()
        
        response = client.post(f'/reorder_lineup/{instance.id}', json={
            'signup_ids': [signup2.id, signup1.id]
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        
        # Verify positions were updated
        db.session.refresh(signup1)
        db.session.refresh(signup2)
        assert signup1.position == 2
        assert signup2.position == 1


class TestErrorHandling:
    """Test error handling in routes."""
    
    def test_nonexistent_show_404(self, client):
        """Test accessing nonexistent show returns 404."""
        response = client.get('/api/show/99999')
        assert response.status_code == 404
    
    def test_nonexistent_event_404(self, client):
        """Test accessing nonexistent event returns 404."""
        response = client.get('/event/99999')
        assert response.status_code == 404
    
    @patch('routes.current_user')
    def test_invalid_json_400(self, mock_current_user, client):
        """Test invalid JSON returns 400."""
        mock_current_user.is_authenticated = True
        mock_current_user.id = "test-user-123"
        
        response = client.post('/api/show', 
                             data='invalid json', 
                             content_type='application/json')
        assert response.status_code == 400