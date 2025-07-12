#!/usr/bin/env python3
"""
Unit tests for models.py
"""
import pytest

pytestmark = pytest.mark.unit
import tempfile
import os
from datetime import date, datetime, time, timedelta
from unittest.mock import patch, MagicMock

from app import app, db
from models import User, Show, ShowRunner, ShowHost, ShowInstance, ShowInstanceHost, Signup, OAuth


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
def sample_user():
    """Create a sample user for testing."""
    user = User(
        id="test-user-123",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        username="testuser",
        profile_image_url="https://example.com/profile.jpg"
    )
    return user


@pytest.fixture
def sample_show(sample_user):
    """Create a sample show for testing."""
    show = Show(
        name="Test Comedy Show",
        venue="Test Venue",
        address="123 Comedy St, Boston, MA",
        timezone="America/New_York",
        description="A test comedy show",
        day_of_week="Monday",
        start_time=time(19, 0),  # 7:00 PM
        end_time=time(21, 0),    # 9:00 PM
        max_signups=10,
        signups_open=2880,  # 2 days before
        signups_closed=0,   # At show start
        owner_id=sample_user.id,
        default_host_id=sample_user.id
    )
    return show


class TestUser:
    """Test User model functionality."""
    
    def test_user_creation(self, app_context, sample_user):
        """Test basic user creation and properties."""
        db.session.add(sample_user)
        db.session.commit()
        
        user = User.query.filter_by(id="test-user-123").first()
        assert user is not None
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.username == "testuser"
        assert user.email_verified is True  # Default for Replit Auth
    
    def test_user_full_name_property(self, app_context):
        """Test full_name property with various scenarios."""
        # Test with first and last name
        user1 = User(id="1", first_name="John", last_name="Doe")
        assert user1.full_name == "John Doe"
        
        # Test with only first name
        user2 = User(id="2", first_name="Jane", last_name="")
        assert user2.full_name == "Jane"
        
        # Test with only last name
        user3 = User(id="3", first_name="", last_name="Smith")
        assert user3.full_name == "Smith"
        
        # Test with username only
        user4 = User(id="4", first_name="", last_name="", username="testuser")
        assert user4.full_name == "testuser"
        
        # Test with email only
        user5 = User(id="5", first_name="", last_name="", username="", email="test@example.com")
        assert user5.full_name == "test@example.com"
        
        # Test with ID only
        user6 = User(id="6", first_name="", last_name="", username="", email="")
        assert user6.full_name == "User 6"
    
    def test_user_password_methods(self, app_context, sample_user):
        """Test password setting and checking methods."""
        sample_user.set_password("testpassword123")
        assert sample_user.password_hash is not None
        assert sample_user.check_password("testpassword123") is True
        assert sample_user.check_password("wrongpassword") is False
    
    def test_user_email_verification(self, app_context, sample_user):
        """Test email verification methods."""
        token = sample_user.generate_verification_token()
        assert token is not None
        assert sample_user.email_verification_token == token
        
        sample_user.verify_email()
        assert sample_user.email_verified is True
        assert sample_user.email_verification_token is None
    
    def test_user_show_role_methods(self, app_context, sample_user, sample_show):
        """Test show role checking methods."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        # Test owner role
        assert sample_user.get_show_role(sample_show) == "owner"
        assert sample_user.can_edit_show(sample_show) is True
        assert sample_user.can_manage_lineup(sample_show) is True
        
        # Test comedian role (different user)
        other_user = User(id="other-user", email="other@example.com")
        db.session.add(other_user)
        db.session.commit()
        
        assert other_user.get_show_role(sample_show) == "comedian"
        assert other_user.can_edit_show(sample_show) is False
        assert other_user.can_manage_lineup(sample_show) is False


class TestShow:
    """Test Show model functionality."""
    
    def test_show_creation(self, app_context, sample_user, sample_show):
        """Test basic show creation and properties."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        show = Show.query.filter_by(name="Test Comedy Show").first()
        assert show is not None
        assert show.venue == "Test Venue"
        assert show.day_of_week == "Monday"
        assert show.start_time == time(19, 0)
        assert show.is_active is True
        assert show.is_deleted is False
    
    def test_show_soft_delete(self, app_context, sample_user, sample_show):
        """Test soft delete functionality."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        show = Show.query.first()
        assert show.is_active is True
        
        show.soft_delete()
        assert show.is_deleted is True
        assert show.ended_date == date.today()
        assert show.is_active is False
        
        show.undelete()
        assert show.is_deleted is False
        assert show.ended_date is None
        assert show.is_active is True
    
    def test_show_time_conversion_methods(self, app_context):
        """Test time conversion utility methods."""
        # Test convert_time_to_minutes
        assert Show.convert_time_to_minutes(2, "minutes") == 2
        assert Show.convert_time_to_minutes(2, "hours") == 120
        assert Show.convert_time_to_minutes(2, "days") == 2880
        assert Show.convert_time_to_minutes(2, "weeks") == 20160
        assert Show.convert_time_to_minutes(2, "months") == 86400
        
        # Test convert_minutes_to_time_unit
        assert Show.convert_minutes_to_time_unit(0) == (0, "minutes")
        assert Show.convert_minutes_to_time_unit(120) == (2, "hours")
        assert Show.convert_minutes_to_time_unit(2880) == (2, "days")
        assert Show.convert_minutes_to_time_unit(20160) == (2, "weeks")
        assert Show.convert_minutes_to_time_unit(86400) == (2, "months")
        assert Show.convert_minutes_to_time_unit(45) == (45, "minutes")
    
    @patch('models.utc_to_local')
    def test_show_signup_datetime_methods(self, mock_utc_to_local, app_context, sample_user, sample_show):
        """Test signup datetime calculation methods."""
        mock_utc_to_local.return_value = datetime(2024, 1, 15, 12, 0)
        
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        test_date = date(2024, 1, 15)
        
        # Test signup open datetime
        open_dt = sample_show.get_signup_open_datetime(test_date)
        assert mock_utc_to_local.called
        
        # Test signup closed datetime
        closed_dt = sample_show.get_signup_closed_datetime(test_date)
        assert mock_utc_to_local.called
    
    def test_show_next_instance_date(self, app_context, sample_user, sample_show):
        """Test next instance date calculation."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        # Test with weekly cadence
        sample_show.repeat_cadence = "weekly"
        sample_show.started_date = date(2024, 1, 8)  # Monday
        
        from_date = date(2024, 1, 10)  # Wednesday
        next_date = sample_show.get_next_instance_date(from_date)
        assert next_date.strftime("%A") == "Monday"
        assert next_date > from_date


class TestShowInstance:
    """Test ShowInstance model functionality."""
    
    def test_show_instance_creation(self, app_context, sample_user, sample_show):
        """Test basic show instance creation."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        assert instance.show == sample_show
        assert instance.instance_date == date(2024, 1, 15)
        assert instance.is_cancelled is False
    
    def test_show_instance_properties(self, app_context, sample_user, sample_show):
        """Test show instance properties that fall back to show defaults."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        # Test defaults
        assert instance.max_signups == sample_show.max_signups
        assert instance.start_time == sample_show.start_time
        assert instance.end_time == sample_show.end_time
        
        # Test overrides
        instance.max_signups_override = 5
        instance.start_time_override = time(20, 0)
        instance.end_time_override = time(22, 0)
        
        assert instance.max_signups == 5
        assert instance.start_time == time(20, 0)
        assert instance.end_time == time(22, 0)
    
    def test_show_instance_cancellation(self, app_context, sample_user, sample_show):
        """Test show instance cancellation and restoration."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        # Test cancellation
        instance.cancel("Test reason")
        assert instance.is_cancelled is True
        assert instance.cancellation_reason == "Test reason"
        assert instance.cancelled_at is not None
        
        # Test restoration
        instance.uncancel()
        assert instance.is_cancelled is False
        assert instance.cancellation_reason is None
        assert instance.cancelled_at is None
    
    def test_show_instance_hosts(self, app_context, sample_user, sample_show):
        """Test show instance host management."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        # Test default host
        hosts = instance.get_hosts()
        assert len(hosts) == 1
        assert hosts[0] == sample_user
        
        # Test host names
        host_names = instance.get_host_names()
        assert host_names == sample_user.full_name
    
    @patch('models.datetime')
    @patch('models.local_to_utc')
    def test_show_instance_signup_status(self, mock_local_to_utc, mock_datetime, app_context, sample_user, sample_show):
        """Test signup status checking."""
        # Mock current time
        mock_datetime.now.return_value = datetime(2024, 1, 15, 12, 0)
        mock_local_to_utc.return_value = datetime(2024, 1, 15, 12, 0)
        
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        # Mock the show's signup datetime methods
        with patch.object(sample_show, 'get_signup_open_datetime') as mock_open, \
             patch.object(sample_show, 'get_signup_closed_datetime') as mock_closed:
            
            mock_open.return_value = datetime(2024, 1, 13, 12, 0)
            mock_closed.return_value = datetime(2024, 1, 15, 19, 0)
            
            status = instance.get_signup_status()
            assert status['status'] == 'open'
            assert status['can_signup'] is True


class TestSignup:
    """Test Signup model functionality."""
    
    def test_signup_creation(self, app_context, sample_user, sample_show):
        """Test basic signup creation."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        signup = Signup(
            comedian_id=sample_user.id,
            show_instance_id=instance.id,
            notes="Test signup notes"
        )
        db.session.add(signup)
        db.session.commit()
        
        assert signup.comedian == sample_user
        assert signup.show_instance == instance
        assert signup.notes == "Test signup notes"
        assert signup.performed is False
    
    def test_signup_show_property(self, app_context, sample_user, sample_show):
        """Test signup show property."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
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
        
        assert signup.show == sample_show


class TestOAuth:
    """Test OAuth model functionality."""
    
    def test_oauth_creation(self, app_context, sample_user):
        """Test OAuth token storage creation."""
        db.session.add(sample_user)
        db.session.commit()
        
        oauth = OAuth(
            user_id=sample_user.id,
            browser_session_key="test-session-key",
            provider="replit_auth",
            token={"access_token": "test-token", "refresh_token": "refresh-token"}
        )
        db.session.add(oauth)
        db.session.commit()
        
        assert oauth.user == sample_user
        assert oauth.browser_session_key == "test-session-key"
        assert oauth.provider == "replit_auth"
        assert oauth.token["access_token"] == "test-token"


class TestShowRoleModels:
    """Test ShowRunner and ShowHost models."""
    
    def test_show_runner_creation(self, app_context, sample_user, sample_show):
        """Test ShowRunner creation."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        runner = ShowRunner(
            show_id=sample_show.id,
            user_id=sample_user.id,
            added_by_id=sample_user.id
        )
        db.session.add(runner)
        db.session.commit()
        
        assert runner.show == sample_show
        assert runner.user == sample_user
        assert runner.added_at is not None
    
    def test_show_host_creation(self, app_context, sample_user, sample_show):
        """Test ShowHost creation."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        host = ShowHost(
            show_id=sample_show.id,
            user_id=sample_user.id,
            added_by_id=sample_user.id
        )
        db.session.add(host)
        db.session.commit()
        
        assert host.show == sample_show
        assert host.user == sample_user
        assert host.added_at is not None
    
    def test_show_instance_host_creation(self, app_context, sample_user, sample_show):
        """Test ShowInstanceHost creation."""
        db.session.add(sample_user)
        db.session.add(sample_show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=sample_show.id,
            instance_date=date(2024, 1, 15)
        )
        db.session.add(instance)
        db.session.commit()
        
        instance_host = ShowInstanceHost(
            show_instance_id=instance.id,
            user_id=sample_user.id
        )
        db.session.add(instance_host)
        db.session.commit()
        
        assert instance_host.show_instance == instance
        assert instance_host.user == sample_user
        assert instance_host.added_at is not None