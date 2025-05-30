"""
Integration tests for the Comedy Open Mic Manager application.
Tests the complete user journey with the new Show/ShowInstance model.
"""

import pytest
import tempfile
import os
from datetime import datetime, date, time, timedelta
from app import app, db
from models import User, Show, ShowInstance, Signup


@pytest.fixture
def client():
    """Create a test client."""
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            
    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


def test_user_registration_and_login(client):
    """Test user registration and login functionality."""
    
    # Test registration
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'password': 'testpass123',
        'password2': 'testpass123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Registration successful' in response.data
    
    # Test login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    

def test_show_creation_and_instances(client):
    """Test creating shows and automatic instance generation."""
    
    # Register and login a user
    client.post('/register', data={
        'username': 'hostuser',
        'email': 'host@example.com',
        'first_name': 'Host',
        'last_name': 'User',
        'password': 'testpass123',
        'password2': 'testpass123'
    })
    
    client.post('/login', data={
        'username': 'hostuser',
        'password': 'testpass123'
    })
    
    # Create a show
    response = client.post('/host/create-event', data={
        'name': 'Weekly Comedy Night',
        'venue': 'The Laugh Track',
        'address': '123 Comedy St, Boston, MA',
        'day_of_week': 'Wednesday',
        'start_time': '19:30',
        'end_time': '21:30',
        'max_signups': '20',
        'signup_deadline_hours': '2',
        'description': 'A fun weekly comedy show'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify show was created
    with app.app_context():
        show = Show.query.first()
        assert show is not None
        assert show.name == 'Weekly Comedy Night'
        assert show.venue == 'The Laugh Track'
        assert show.day_of_week == 'Wednesday'


def test_dashboard_access(client):
    """Test dashboard access for different user types."""
    
    # Register and login
    client.post('/register', data={
        'username': 'dashuser',
        'email': 'dash@example.com',
        'first_name': 'Dash',
        'last_name': 'User',
        'password': 'testpass123',
        'password2': 'testpass123'
    })
    
    client.post('/login', data={
        'username': 'dashuser',
        'password': 'testpass123'
    })
    
    # Test main dashboard
    response = client.get('/dashboard')
    assert response.status_code == 200
    
    # Test comedian dashboard
    response = client.get('/comedian/dashboard')
    assert response.status_code == 200
    
    # Test host dashboard
    response = client.get('/host/dashboard')
    assert response.status_code == 200


def test_calendar_functionality(client):
    """Test calendar view and API endpoints."""
    
    # Register and login
    client.post('/register', data={
        'username': 'caluser',
        'email': 'cal@example.com',
        'first_name': 'Cal',
        'last_name': 'User',
        'password': 'testpass123',
        'password2': 'testpass123'
    })
    
    client.post('/login', data={
        'username': 'caluser',
        'password': 'testpass123'
    })
    
    # Test calendar view
    response = client.get('/calendar')
    assert response.status_code == 200
    
    # Test calendar API
    response = client.get('/api/calendar/events')
    assert response.status_code == 200
    assert response.content_type == 'application/json'


def test_event_info_pages(client):
    """Test event information pages."""
    
    # Create a user and show
    with app.app_context():
        user = User(
            username='eventuser',
            email='event@example.com',
            first_name='Event',
            last_name='User'
        )
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        show = Show(
            name='Test Show',
            venue='Test Venue',
            address='Test Address',
            day_of_week='Friday',
            start_time=time(19, 0),
            end_time=time(21, 0),
            owner_id=user.id
        )
        db.session.add(show)
        db.session.commit()
        
        instance = ShowInstance(
            show_id=show.id,
            instance_date=date.today() + timedelta(days=7)
        )
        db.session.add(instance)
        db.session.commit()
        
        instance_id = instance.id
    
    # Test event info page
    response = client.get(f'/event/{instance_id}')
    assert response.status_code == 200
    
    # Test live lineup page
    response = client.get(f'/live/{instance_id}')
    assert response.status_code == 200


def test_authentication_redirects(client):
    """Test that protected routes redirect to login."""
    
    # Test protected routes redirect to login
    protected_routes = [
        '/dashboard',
        '/comedian/dashboard',
        '/host/dashboard',
        '/calendar',
        '/host/create-event'
    ]
    
    for route in protected_routes:
        response = client.get(route)
        assert response.status_code == 302  # Redirect to login


def test_public_routes(client):
    """Test that public routes are accessible without login."""
    
    # Test homepage
    response = client.get('/')
    assert response.status_code == 200
    
    # Test registration page
    response = client.get('/register')
    assert response.status_code == 200
    
    # Test login page
    response = client.get('/login')
    assert response.status_code == 200


def test_user_model_functionality(client):
    """Test User model methods and properties."""
    
    with app.app_context():
        user = User(
            username='modeluser',
            email='model@example.com',
            first_name='Model',
            last_name='User'
        )
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        # Test password verification
        assert user.check_password('testpass123') is True
        assert user.check_password('wrongpass') is False
        
        # Test full name property
        assert user.full_name == 'Model User'
        
        # Test email verification token generation
        token = user.generate_verification_token()
        assert token is not None
        assert user.email_verification_token == token


def test_show_model_functionality(client):
    """Test Show model methods and properties."""
    
    with app.app_context():
        user = User(
            username='showuser',
            email='show@example.com',
            first_name='Show',
            last_name='User'
        )
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        show = Show(
            name='Test Show',
            venue='Test Venue',
            address='Test Address',
            day_of_week='Monday',
            start_time=time(20, 0),
            end_time=time(22, 0),
            owner_id=user.id
        )
        db.session.add(show)
        db.session.commit()
        
        # Test show is active by default
        assert show.is_active is True
        
        # Test soft delete functionality
        show.soft_delete()
        assert show.is_deleted is True
        assert show.ended_date is not None
        
        # Test undelete functionality
        show.undelete()
        assert show.is_deleted is False
        assert show.ended_date is None


if __name__ == '__main__':
    pytest.main([__file__])