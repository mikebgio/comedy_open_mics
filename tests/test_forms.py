#!/usr/bin/env python3
"""
Unit tests for forms.py
"""
import pytest

pytestmark = pytest.mark.unit
import tempfile
import os
from unittest.mock import patch, MagicMock

from app import app, db
from forms import (
    RegistrationForm, LoginForm, EventForm, SignupForm, 
    CancellationForm, ShowSettingsForm, InstanceHostForm
)
from models import User, Show


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


class TestRegistrationForm:
    """Test RegistrationForm functionality."""
    
    def test_registration_form_valid_data(self, app_context):
        """Test registration form with valid data."""
        with app.test_request_context():
            form = RegistrationForm(
                username="testuser",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                password="testpass123",
                password2="testpass123"
            )
            assert form.validate() is True
    
    def test_registration_form_invalid_email(self, app_context):
        """Test registration form with invalid email."""
        with app.test_request_context():
            form = RegistrationForm(
                username="testuser",
                email="invalid-email",
                first_name="Test",
                last_name="User",
                password="testpass123",
                password2="testpass123"
            )
            assert form.validate() is False
            assert any("email" in str(error).lower() for error in form.email.errors)
    
    def test_registration_form_password_mismatch(self, app_context):
        """Test registration form with password mismatch."""
        with app.test_request_context():
            form = RegistrationForm(
                username="testuser",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                password="testpass123",
                password2="differentpass"
            )
            assert form.validate() is False
            assert any("match" in str(error).lower() for error in form.password2.errors)
    
    def test_registration_form_short_password(self, app_context):
        """Test registration form with short password."""
        with app.test_request_context():
            form = RegistrationForm(
                username="testuser",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                password="short",
                password2="short"
            )
            assert form.validate() is False
            assert any("6" in str(error) for error in form.password.errors)
    
    def test_registration_form_username_validation(self, app_context):
        """Test registration form username validation with existing user."""
        # Create existing user
        existing_user = User(
            id="existing-user",
            username="existinguser",
            email="existing@example.com"
        )
        db.session.add(existing_user)
        db.session.commit()
        
        with app.test_request_context():
            form = RegistrationForm(
                username="existinguser",
                email="new@example.com",
                first_name="New",
                last_name="User",
                password="testpass123",
                password2="testpass123"
            )
            assert form.validate() is False
            assert any("username" in str(error).lower() for error in form.username.errors)
    
    def test_registration_form_email_validation(self, app_context):
        """Test registration form email validation with existing user."""
        # Create existing user
        existing_user = User(
            id="existing-user",
            username="existinguser",
            email="existing@example.com"
        )
        db.session.add(existing_user)
        db.session.commit()
        
        with app.test_request_context():
            form = RegistrationForm(
                username="newuser",
                email="existing@example.com",
                first_name="New",
                last_name="User",
                password="testpass123",
                password2="testpass123"
            )
            assert form.validate() is False
            assert any("email" in str(error).lower() for error in form.email.errors)


class TestLoginForm:
    """Test LoginForm functionality."""
    
    def test_login_form_valid_data(self, app_context):
        """Test login form with valid data."""
        with app.test_request_context():
            form = LoginForm(
                username="testuser",
                password="testpass123"
            )
            assert form.validate() is True
    
    def test_login_form_missing_username(self, app_context):
        """Test login form with missing username."""
        with app.test_request_context():
            form = LoginForm(
                username="",
                password="testpass123"
            )
            assert form.validate() is False
            assert any("required" in str(error).lower() for error in form.username.errors)
    
    def test_login_form_missing_password(self, app_context):
        """Test login form with missing password."""
        with app.test_request_context():
            form = LoginForm(
                username="testuser",
                password=""
            )
            assert form.validate() is False
            assert any("required" in str(error).lower() for error in form.password.errors)


class TestEventForm:
    """Test EventForm functionality."""
    
    def test_event_form_valid_data(self, app_context):
        """Test event form with valid data."""
        with app.test_request_context():
            form = EventForm(
                name="Test Comedy Show",
                venue="Test Venue",
                address="123 Comedy St, Boston, MA",
                day_of_week="Monday",
                start_time="19:00",
                end_time="21:00",
                description="Test description",
                max_signups=10,
                signups_open_value=2,
                signups_open_unit="days",
                signups_closed_value=0,
                signups_closed_unit="minutes",
                signup_deadline_hours=2,
                show_host_info=True,
                show_owner_info=False
            )
            assert form.validate() is True
    
    def test_event_form_invalid_max_signups(self, app_context):
        """Test event form with invalid max signups."""
        with app.test_request_context():
            form = EventForm(
                name="Test Comedy Show",
                venue="Test Venue",
                address="123 Comedy St, Boston, MA",
                day_of_week="Monday",
                start_time="19:00",
                max_signups=0,  # Invalid: must be at least 1
                signups_open_value=2,
                signups_open_unit="days",
                signups_closed_value=0,
                signups_closed_unit="minutes",
                signup_deadline_hours=2
            )
            assert form.validate() is False
            assert any(error for error in form.max_signups.errors)
    
    def test_event_form_invalid_signup_timing(self, app_context):
        """Test event form with invalid signup timing."""
        with app.test_request_context():
            form = EventForm(
                name="Test Comedy Show",
                venue="Test Venue",
                address="123 Comedy St, Boston, MA",
                day_of_week="Monday",
                start_time="19:00",
                max_signups=10,
                signups_open_value=-1,  # Invalid: negative value
                signups_open_unit="days",
                signups_closed_value=0,
                signups_closed_unit="minutes",
                signup_deadline_hours=2
            )
            assert form.validate() is False
            assert any(error for error in form.signups_open_value.errors)
    
    def test_event_form_missing_required_fields(self, app_context):
        """Test event form with missing required fields."""
        with app.test_request_context():
            form = EventForm(
                name="",  # Missing required field
                venue="Test Venue",
                address="123 Comedy St, Boston, MA",
                day_of_week="Monday",
                start_time="19:00",
                max_signups=10,
                signups_open_value=2,
                signups_open_unit="days",
                signups_closed_value=0,
                signups_closed_unit="minutes",
                signup_deadline_hours=2
            )
            assert form.validate() is False
            assert any("required" in str(error).lower() for error in form.name.errors)


class TestSignupForm:
    """Test SignupForm functionality."""
    
    def test_signup_form_valid_data(self, app_context):
        """Test signup form with valid data."""
        with app.test_request_context():
            form = SignupForm(
                notes="Looking forward to performing!"
            )
            assert form.validate() is True
    
    def test_signup_form_empty_notes(self, app_context):
        """Test signup form with empty notes (should be valid)."""
        with app.test_request_context():
            form = SignupForm(
                notes=""
            )
            assert form.validate() is True
    
    def test_signup_form_long_notes(self, app_context):
        """Test signup form with notes that are too long."""
        with app.test_request_context():
            form = SignupForm(
                notes="x" * 501  # Over 500 character limit
            )
            assert form.validate() is False
            assert any("500" in str(error) for error in form.notes.errors)


class TestCancellationForm:
    """Test CancellationForm functionality."""
    
    def test_cancellation_form_valid_data(self, app_context):
        """Test cancellation form with valid data."""
        from datetime import date
        
        with app.test_request_context():
            form = CancellationForm(
                cancelled_date=date(2024, 12, 25),
                reason="Holiday closure"
            )
            assert form.validate() is True
    
    def test_cancellation_form_missing_date(self, app_context):
        """Test cancellation form with missing date."""
        with app.test_request_context():
            form = CancellationForm(
                cancelled_date=None,
                reason="Holiday closure"
            )
            assert form.validate() is False
            assert any("required" in str(error).lower() for error in form.cancelled_date.errors)
    
    def test_cancellation_form_long_reason(self, app_context):
        """Test cancellation form with reason that's too long."""
        with app.test_request_context():
            form = CancellationForm(
                cancelled_date=date(2024, 12, 25),
                reason="x" * 201  # Over 200 character limit
            )
            assert form.validate() is False
            assert any("200" in str(error) for error in form.reason.errors)


class TestShowSettingsForm:
    """Test ShowSettingsForm functionality."""
    
    def test_show_settings_form_initialization(self, app_context):
        """Test ShowSettingsForm initialization with show."""
        # Create a test user and show
        user = User(id="test-user", username="testuser", email="test@example.com")
        show = Show(
            name="Test Show",
            venue="Test Venue",
            address="123 Test St",
            day_of_week="Monday",
            start_time="19:00",
            max_signups=10,
            owner_id=user.id
        )
        db.session.add(user)
        db.session.add(show)
        db.session.commit()
        
        with app.test_request_context():
            form = ShowSettingsForm(show=show)
            assert form.default_host_id.choices is not None
            assert any(choice[0] == user.id for choice in form.default_host_id.choices)


class TestInstanceHostForm:
    """Test InstanceHostForm functionality."""
    
    def test_instance_host_form_initialization(self, app_context):
        """Test InstanceHostForm initialization with show."""
        # Create a test user and show
        user = User(id="test-user", username="testuser", email="test@example.com")
        show = Show(
            name="Test Show",
            venue="Test Venue", 
            address="123 Test St",
            day_of_week="Monday",
            start_time="19:00",
            max_signups=10,
            owner_id=user.id
        )
        db.session.add(user)
        db.session.add(show)
        db.session.commit()
        
        with app.test_request_context():
            form = InstanceHostForm(show=show)
            assert form.host_id.choices is not None
            assert any(choice[0] == user.id for choice in form.host_id.choices)
    
    def test_instance_host_form_valid_selection(self, app_context):
        """Test InstanceHostForm with valid host selection."""
        # Create a test user and show
        user = User(id="test-user", username="testuser", email="test@example.com")
        show = Show(
            name="Test Show",
            venue="Test Venue",
            address="123 Test St", 
            day_of_week="Monday",
            start_time="19:00",
            max_signups=10,
            owner_id=user.id
        )
        db.session.add(user)
        db.session.add(show)
        db.session.commit()
        
        with app.test_request_context():
            form = InstanceHostForm(show=show, host_id=user.id)
            assert form.validate() is True