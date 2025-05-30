#!/usr/bin/env python3
"""
Integration tests for Comedy Open Mic Manager
Tests the full workflow from user registration to event management
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
    """Test complete user journey from registration to event participation."""

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
    assert b"Registration successful" in response.data

    # 2. Login as comedian
    response = client.post(
        "/login",
        data={"username": "testcomedian", "password": "testpass123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Dashboard" in response.data

    # 3. Create an event (user becomes host)
    response = client.post(
        "/host/create_event",
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
    assert b"Event created successfully" in response.data

    # 4. Verify user is now both comedian and host
    with app.app_context():
        user = User.query.filter_by(username="testcomedian").first()
        assert user.is_host == True
        assert user.is_comedian == True

    # 5. Register another comedian
    client.get("/logout")
    response = client.post(
        "/register",
        data={
            "username": "comedian2",
            "email": "comedian2@test.com",
            "first_name": "Second",
            "last_name": "Comedian",
            "password": "testpass123",
            "password2": "testpass123",
        },
        follow_redirects=True,
    )

    # 6. Login as second comedian
    client.post(
        "/login",
        data={"username": "comedian2", "password": "testpass123"},
        follow_redirects=True,
    )

    # 7. Sign up for the event
    with app.app_context():
        event = Event.query.filter_by(name="Weekly Comedy Night").first()
        event_id = event.id

    response = client.post(
        f"/comedian/signup/{event_id}",
        data={"notes": "Excited to perform my new set!"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Successfully signed up" in response.data

    # 8. Check live lineup
    response = client.get(f"/lineup/{event_id}")
    assert response.status_code == 200
    assert b"Weekly Comedy Night" in response.data
    assert b"Second Comedian" in response.data


def test_event_management_workflow(client):
    """Test event management features for hosts."""

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

    # Create event
    client.post(
        "/host/create_event",
        data={
            "name": "Test Event",
            "venue": "Test Venue",
            "address": "456 Test Ave, Boston, MA",
            "day_of_week": "Thursday",
            "start_time": "20:00",
            "end_time": "",  # No end time
            "description": "Test event description",
            "max_signups": "15",
            "signup_deadline_hours": "3",
        },
    )

    # Access host dashboard
    response = client.get("/host/dashboard")
    assert response.status_code == 200
    assert b"Test Event" in response.data

    # Access lineup management
    with app.app_context():
        event = Event.query.filter_by(name="Test Event").first()
        event_id = event.id

    response = client.get(f"/host/manage_lineup/{event_id}")
    assert response.status_code == 200
    assert b"Manage Lineup" in response.data


def test_api_endpoints(client):
    """Test API endpoints used by JavaScript."""

    # Register host and create event
    client.post(
        "/register",
        data={
            "username": "apihost",
            "email": "api@test.com",
            "first_name": "API",
            "last_name": "Host",
            "password": "testpass123",
            "password2": "testpass123",
        },
    )

    client.post("/login", data={"username": "apihost", "password": "testpass123"})

    client.post(
        "/host/create_event",
        data={
            "name": "API Test Event",
            "venue": "API Venue",
            "address": "789 API St, Boston, MA",
            "day_of_week": "Friday",
            "start_time": "21:00",
            "description": "API test event",
            "max_signups": "10",
            "signup_deadline_hours": "1",
        },
    )

    with app.app_context():
        event = Event.query.filter_by(name="API Test Event").first()
        event_id = event.id

    # Test lineup reordering endpoint
    response = client.post(
        f"/host/reorder_lineup/{event_id}",
        json={"lineup_order": []},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200


def test_error_handling(client):
    """Test error handling and edge cases."""

    # Test accessing non-existent event
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
