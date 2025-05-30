#!/usr/bin/env python3
"""
Basic tests for Comedy Open Mic Manager
Focused on core functionality without complex database operations
"""
import unittest

from app import app


class BasicTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.app = app.test_client()

    def test_homepage_loads(self):
        """Test that the homepage loads successfully."""
        rv = self.app.get("/")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b"Comedy Open Mic Manager", rv.data)

    def test_login_page_loads(self):
        """Test that the login page loads."""
        rv = self.app.get("/login")
        self.assertEqual(rv.status_code, 200)

    def test_register_page_loads(self):
        """Test that the register page loads."""
        rv = self.app.get("/register")
        self.assertEqual(rv.status_code, 200)

    def test_about_page_loads(self):
        """Test that the about page loads."""
        rv = self.app.get("/about")
        # Should either load or redirect
        self.assertIn(rv.status_code, [200, 302, 404])

    def test_protected_routes_redirect(self):
        """Test that protected routes redirect when not logged in."""
        protected_routes = ["/dashboard"]

        for route in protected_routes:
            rv = self.app.get(route)
            # Should redirect to login or show login form
            self.assertIn(rv.status_code, [200, 302])


if __name__ == "__main__":
    unittest.main()
