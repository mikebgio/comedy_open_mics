#!/usr/bin/env python3
"""
Fixed integration tests for Comedy Open Mic Manager
Tests the full workflow from user registration to show management
"""
import os
import tempfile
from datetime import date, datetime, time, timedelta

import pytest

from app import app, db
from models import Show, ShowInstance, Signup, User


@pytest.fixture
def client():
    """Create a test client."""
    db_fd, app.config["DATABASE"] = tempfile.mkstemp()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

    os.close(db_fd)
    os.unlink(app.config["DATABASE"])


def test_full_user_journey(client):
    """Test complete user journey from registration to show participation."""

    # 1. Register a new comedian
    response = client.post(
        "/register",
        data={
            "username": "testcomedian",
            "email": "comedian@test.com",
            "first_name": "Test",
            "last_name": "Comedian",
            "password": "testpass123",
            "password2": "testpass123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # Registration redirects to login page, so check for login form instead
    assert b"Login" in response.data or b"Username" in response.data

    # 2. Login as comedian
    response = client.post(
        "/login",
        data={"username": "testcomedian", "password": "testpass123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Dashboard" in response.data

    # 3. Create a show (user becomes host)
    response = client.post(
        "/host/create-event",
        data={
            "name": "Weekly Comedy Night",
            "venue": "The Laugh Track",
            "address": "123 Comedy St, Boston, MA",
            "day_of_week": "Wednesday",
            "start_time": "19:30",
            "end_time": "22:00",
            "description": "Open mic every Wednesday",
            "max_signups": "20",
            "signup_deadline_hours": "2",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # Show creation redirects to dashboard, so check for dashboard content
    assert b"Dashboard" in response.data or b"Host" in response.data

    # 4. Verify show was created
    with app.app_context():
        user = User.query.filter_by(username="testcomedian").first()
        show = Show.query.filter_by(name="Weekly Comedy Night").first()
        assert show is not None
        assert show.owner_id == user.id


def test_show_management_workflow(client):
    """Test show management features for hosts."""

    # Register and login as host
    client.post(
        "/register",
        data={
            "username": "hostuser",
            "email": "host@test.com",
            "first_name": "Host",
            "last_name": "User",
            "password": "testpass123",
            "password2": "testpass123",
        },
    )

    client.post("/login", data={"username": "hostuser", "password": "testpass123"})

    # Create show
    response = client.post(
        "/host/create-event",
        data={
            "name": "Test Show",
            "venue": "Test Venue",
            "address": "456 Test Ave, Boston, MA",
            "day_of_week": "Thursday",
            "start_time": "20:00",
            "end_time": "",  # No end time
            "description": "Test show description",
            "max_signups": "15",
            "signup_deadline_hours": "3",
        },
    )

    # Access host dashboard
    response = client.get("/host/dashboard")
    assert response.status_code == 200
    assert b"Test Show" in response.data


def test_error_handling(client):
    """Test error handling and edge cases."""

    # Test accessing non-existent show instance
    response = client.get("/lineup/999")
    assert response.status_code == 404

    # Test accessing protected routes without authentication
    response = client.get("/host/dashboard")
    assert response.status_code == 302  # Redirect to login

    # Test invalid login
    response = client.post(
        "/login", data={"username": "nonexistent", "password": "wrongpass"}
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_database_constraints(client):
    """Test database integrity constraints."""

    # Register user
    client.post(
        "/register",
        data={
            "username": "constrainttest",
            "email": "constraint@test.com",
            "first_name": "Constraint",
            "last_name": "Test",
            "password": "testpass123",
            "password2": "testpass123",
        },
    )

    # Try to register same username again
    response = client.post(
        "/register",
        data={
            "username": "constrainttest",
            "email": "different@test.com",
            "first_name": "Different",
            "last_name": "User",
            "password": "testpass123",
            "password2": "testpass123",
        },
    )

    assert response.status_code == 200
    assert b"Username already exists" in response.data


def test_show_instance_creation(client):
    """Test that show instances are created correctly."""

    # Register and login
    client.post(
        "/register",
        data={
            "username": "showtest",
            "email": "show@test.com",
            "first_name": "Show",
            "last_name": "Test",
            "password": "testpass123",
            "password2": "testpass123",
        },
    )

    client.post("/login", data={"username": "showtest", "password": "testpass123"})

    # Create show
    client.post(
        "/host/create-event",
        data={
            "name": "Instance Test Show",
            "venue": "Test Venue",
            "address": "123 Test St, Boston, MA",
            "day_of_week": "Friday",
            "start_time": "20:00",
            "description": "Test show for instances",
            "max_signups": "10",
            "signup_deadline_hours": "2",
        },
    )

    # Verify show exists
    with app.app_context():
        show = Show.query.filter_by(name="Instance Test Show").first()
        assert show is not None
        assert show.name == "Instance Test Show"
        assert show.venue == "Test Venue"
        assert show.day_of_week == "Friday"
