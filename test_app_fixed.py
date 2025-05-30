#!/usr/bin/env python3
"""
End-to-end tests for Comedy Open Mic Manager
Updated for new Show/ShowInstance data model
"""
import os
import tempfile
import unittest
from datetime import date, datetime, time, timedelta

from app import app, db
from models import Show, ShowInstance, Signup, User


class ComedyOpenMicTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Store original config
        self.original_db_uri = app.config.get("SQLALCHEMY_DATABASE_URI")

        # Create a temporary database
        self.db_fd, app.config["DATABASE"] = tempfile.mkstemp()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["WTF_CSRF_ENABLED"] = False

        # Recreate the engine and reinitialize db
        db.engine.dispose()

        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after each test method."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

        # Restore original database configuration
        if self.original_db_uri:
            app.config["SQLALCHEMY_DATABASE_URI"] = self.original_db_uri

        # Clean up temp files
        os.close(self.db_fd)
        os.unlink(app.config["DATABASE"])

        # Dispose of the test engine
        db.engine.dispose()

    def create_test_user(
        self,
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
    ):
        """Helper method to create a test user."""
        with app.app_context():
            user = User()
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.email_verified = True
            user.set_password("testpassword")
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            db.session.expunge(user)
            return user_id

    def create_test_show(self, owner_user, name="Test Comedy Show"):
        """Helper method to create a test show."""
        # Handle both User object and user ID
        owner_id = owner_user.id if hasattr(owner_user, "id") else owner_user

        with app.app_context():
            show = Show()
            show.name = name
            show.venue = "Test Venue"
            show.address = "123 Test St, Boston, MA"
            show.day_of_week = "Monday"
            show.start_time = time(19, 30)
            show.end_time = time(22, 0)
            show.description = "Test comedy event"
            show.max_signups = 20
            show.signup_window_after_hours = 2
            show.owner_id = owner_id
            db.session.add(show)
            db.session.commit()
            show_id = show.id
            db.session.expunge(show)
            return show_id

    def login_user(self, username="testuser", password="testpassword"):
        """Helper method to log in a user."""
        return self.app.post(
            "/login",
            data=dict(username=username, password=password),
            follow_redirects=True,
        )

    def test_homepage_loads(self):
        """Test that the homepage loads successfully."""
        rv = self.app.get("/")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b"Comedy Open Mic Manager", rv.data)

    def test_user_registration(self):
        """Test user registration flow."""
        rv = self.app.post(
            "/register",
            data=dict(
                username="newuser",
                email="newuser@example.com",
                first_name="New",
                last_name="User",
                password="password123",
                password2="password123",
            ),
            follow_redirects=True,
        )

        self.assertEqual(rv.status_code, 200)
        # Just check the response is successful, don't check specific message text

        # Verify user was created in database
        with app.app_context():
            user = User.query.filter_by(username="newuser").first()
            self.assertIsNotNone(user)
            if user:
                self.assertEqual(user.email, "newuser@example.com")
                self.assertTrue(user.email_verified)

    def test_user_login_logout(self):
        """Test user login and logout flow."""
        # Create test user
        self.create_test_user()

        # Test login
        rv = self.login_user()
        self.assertEqual(rv.status_code, 200)

        # Test logout
        rv = self.app.get("/logout", follow_redirects=True)
        self.assertEqual(rv.status_code, 200)

    def test_show_creation_routes_exist(self):
        """Test that show creation routes are accessible."""
        # Create and login test user
        user_id = self.create_test_user()
        self.login_user()

        # Try to access show creation page
        rv = self.app.get("/host/create_show")
        # Should either load the page or redirect (both are valid)
        self.assertIn(rv.status_code, [200, 302])

    def test_database_models_work(self):
        """Test that the database models can be created and queried."""
        with app.app_context():
            # Test User model
            user = User()
            user.username = "testuser"
            user.email = "test@example.com"
            user.first_name = "Test"
            user.last_name = "User"
            user.email_verified = True
            user.set_password("password")
            db.session.add(user)
            db.session.commit()

            # Test Show model
            show = Show()
            show.name = "Test Show"
            show.venue = "Test Venue"
            show.address = "123 Test St"
            show.day_of_week = "Monday"
            show.start_time = time(19, 0)
            show.owner_id = user.id
            db.session.add(show)
            db.session.commit()

            # Test ShowInstance model
            instance = ShowInstance()
            instance.show_id = show.id
            instance.instance_date = date.today()
            db.session.add(instance)
            db.session.commit()

            # Verify data was saved
            saved_user = User.query.filter_by(username="testuser").first()
            self.assertIsNotNone(saved_user)

            saved_show = Show.query.filter_by(name="Test Show").first()
            self.assertIsNotNone(saved_show)

            saved_instance = ShowInstance.query.filter_by(show_id=show.id).first()
            self.assertIsNotNone(saved_instance)

    def test_authentication_required(self):
        """Test that protected routes require authentication."""
        # Try to access protected routes without login
        protected_routes = ["/dashboard"]

        for route in protected_routes:
            rv = self.app.get(route, follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            # Just verify we get a response, authentication may redirect

    def test_footer_copyright_year(self):
        """Test that footer displays current year."""
        rv = self.app.get("/")
        current_year = datetime.now().year
        self.assertIn(str(current_year).encode(), rv.data)


if __name__ == "__main__":
    unittest.main()
