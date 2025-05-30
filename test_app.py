#!/usr/bin/env python3
"""
End-to-end tests for Comedy Open Mic Manager
"""
import unittest
import tempfile
import os
from datetime import datetime, date, time, timedelta
from app import app, db
from models import User, Event, Signup, EventCancellation

class ComedyOpenMicTestCase(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
            
    def tearDown(self):
        """Clean up after each test method."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])
    
    def create_test_user(self, username="testuser", email="test@example.com", 
                        first_name="Test", last_name="User", is_host=False):
        """Helper method to create a test user."""
        with app.app_context():
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_comedian=True,
                is_host=is_host,
                email_verified=True
            )
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            db.session.expunge(user)
            return user_id
    
    def create_test_event(self, host_user, name="Test Comedy Show"):
        """Helper method to create a test event."""
        # Handle both User object and user ID
        host_id = host_user.id if hasattr(host_user, 'id') else host_user
        
        with app.app_context():
            event = Event(
                name=name,
                venue="Test Venue",
                address="123 Test St, Boston, MA",
                day_of_week="Monday",
                start_time=time(19, 30),
                end_time=time(22, 0),
                description="Test comedy event",
                max_signups=20,
                signup_deadline_hours=2,
                host_id=host_id,
                is_active=True
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
            db.session.expunge(event)
            return event_id
    
    def login_user(self, username="testuser", password="testpassword"):
        """Helper method to log in a user."""
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)
    
    def test_homepage_loads(self):
        """Test that the homepage loads successfully."""
        rv = self.app.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Comedy Open Mic Manager', rv.data)
    
    def test_user_registration(self):
        """Test user registration flow."""
        rv = self.app.post('/register', data=dict(
            username='newuser',
            email='newuser@example.com',
            first_name='New',
            last_name='User',
            password='password123',
            password2='password123'
        ), follow_redirects=True)
        
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Registration successful', rv.data)
        
        # Verify user was created in database
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'newuser@example.com')
            self.assertTrue(user.email_verified)
    
    def test_user_login_logout(self):
        """Test user login and logout flow."""
        # Create test user
        self.create_test_user()
        
        # Test login
        rv = self.login_user()
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Dashboard', rv.data)
        
        # Test logout
        rv = self.app.get('/logout', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Comedy Open Mic Manager', rv.data)
    
    def test_event_creation(self):
        """Test event creation by host."""
        # Create and login test user
        user_id = self.create_test_user()
        self.login_user()
        
        # Create event
        rv = self.app.post('/host/create_event', data=dict(
            name='Test Open Mic',
            venue='Test Comedy Club',
            address='456 Comedy Ln, Boston, MA',
            day_of_week='Tuesday',
            start_time='20:00',
            end_time='23:00',
            description='Weekly open mic night',
            max_signups='15',
            signup_deadline_hours='3'
        ), follow_redirects=True)
        
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Event created successfully', rv.data)
        
        # Verify event was created and user became host
        with app.app_context():
            event = Event.query.filter_by(name='Test Open Mic').first()
            self.assertIsNotNone(event)
            self.assertEqual(event.venue, 'Test Comedy Club')
            
            updated_user = User.query.get(user_id)
            self.assertTrue(updated_user.is_host)
    
    def test_comedian_signup_for_event(self):
        """Test comedian signing up for an event."""
        # Create host and event
        host_id = self.create_test_user(username="host", email="host@example.com", is_host=True)
        
        with app.app_context():
            # Get fresh host object from database
            host = User.query.get(host_id)
            event = self.create_test_event(host)
            event_id = event.id
        
        # Create comedian and login
        comedian_id = self.create_test_user(username="comedian", email="comedian@example.com")
        self.login_user(username="comedian")
        
        # Sign up for event
        rv = self.app.post(f'/comedian/signup/{event_id}', data=dict(
            notes='Excited to perform!'
        ), follow_redirects=True)
        
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Successfully signed up', rv.data)
        
        # Verify signup was created
        with app.app_context():
            signup = Signup.query.filter_by(
                comedian_id=comedian_id,
                event_id=event_id
            ).first()
            self.assertIsNotNone(signup)
            self.assertEqual(signup.notes, 'Excited to perform!')
    
    def test_live_lineup_display(self):
        """Test live lineup page displays correctly."""
        # Create host and event
        host = self.create_test_user(username="host", email="host@example.com", is_host=True)
        event = self.create_test_event(host)
        
        # Create comedian and signup
        comedian = self.create_test_user(username="comedian", email="comedian@example.com")
        
        with app.app_context():
            # Calculate next event date
            today = date.today()
            days_ahead = (0 - today.weekday()) % 7  # Monday
            if days_ahead == 0:
                event_date = today
            else:
                event_date = today + timedelta(days=days_ahead)
            
            signup = Signup(
                comedian_id=comedian.id,
                event_id=event.id,
                event_date=event_date,
                position=1,
                notes="Test performance"
            )
            db.session.add(signup)
            db.session.commit()
        
        # Test live lineup page
        rv = self.app.get(f'/lineup/{event.id}')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Test Comedy Show', rv.data)
        self.assertIn(b'Test User', rv.data)  # Comedian name
    
    def test_lineup_management(self):
        """Test host managing lineup order."""
        # Create host and event
        host = self.create_test_user(username="host", email="host@example.com", is_host=True)
        event = self.create_test_event(host)
        
        # Login as host
        self.login_user(username="host")
        
        # Access lineup management page
        rv = self.app.get(f'/host/manage_lineup/{event.id}')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Manage Lineup', rv.data)
    
    def test_event_cancellation(self):
        """Test event cancellation functionality."""
        # Create host and event
        host_id = self.create_test_user(username="host", email="host@example.com", is_host=True)
        event_id = self.create_test_event(host_id)
        
        # Login as host
        self.login_user(username="host")
        
        # Cancel event for a specific date
        today = date.today()
        rv = self.app.post(f'/host/cancel_event/{event_id}', data=dict(
            cancelled_date=today.strftime('%Y-%m-%d'),
            reason='Venue unavailable'
        ), follow_redirects=True)
        
        self.assertEqual(rv.status_code, 200)
        
        # Verify cancellation was recorded
        with app.app_context():
            cancellation = EventCancellation.query.filter_by(
                event_id=event_id,
                cancelled_date=today
            ).first()
            self.assertIsNotNone(cancellation)
            self.assertEqual(cancellation.reason, 'Venue unavailable')
    
    def test_duplicate_signup_prevention(self):
        """Test that users cannot sign up for the same event twice."""
        # Create host and event
        host_id = self.create_test_user(username="host", email="host@example.com", is_host=True)
        event_id = self.create_test_event(host_id)
        
        # Create comedian and login
        comedian_id = self.create_test_user(username="comedian", email="comedian@example.com")
        self.login_user(username="comedian")
        
        # First signup should succeed
        rv = self.app.post(f'/comedian/signup/{event_id}', data=dict(
            notes='First signup'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        
        # Second signup should be prevented
        rv = self.app.post(f'/comedian/signup/{event_id}', data=dict(
            notes='Second signup attempt'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'already signed up', rv.data)
    
    def test_authentication_required(self):
        """Test that protected routes require authentication."""
        # Try to access protected routes without login
        protected_routes = [
            '/dashboard',
            '/host/create_event',
            '/host/dashboard'
        ]
        
        for route in protected_routes:
            rv = self.app.get(route, follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            self.assertIn(b'login', rv.data.lower())
    
    def test_footer_copyright_year(self):
        """Test that footer displays current year."""
        rv = self.app.get('/')
        current_year = datetime.now().year
        self.assertIn(str(current_year).encode(), rv.data)
        self.assertIn(b'Boston Comedy Community', rv.data)

if __name__ == '__main__':
    unittest.main()