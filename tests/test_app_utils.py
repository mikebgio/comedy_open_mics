#!/usr/bin/env python3
"""
Unit tests for app.py utility functions
"""
import pytest

pytestmark = pytest.mark.unit
import tempfile
import os
from datetime import datetime
from unittest.mock import patch
import pytz

from app import app, db, get_user_timezone, utc_to_local, local_to_utc


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


class TestTimezoneUtilities:
    """Test timezone utility functions."""
    
    def test_get_user_timezone(self, app_context):
        """Test get_user_timezone function."""
        tz = get_user_timezone()
        assert tz.zone == "America/New_York"
        assert isinstance(tz, pytz.tzinfo.BaseTzInfo)
    
    def test_utc_to_local_with_timezone_naive(self, app_context):
        """Test utc_to_local with timezone-naive datetime."""
        utc_dt = datetime(2024, 1, 15, 12, 0, 0)  # Noon UTC
        local_dt = utc_to_local(utc_dt, "America/New_York")
        
        # Should convert to Eastern time (UTC-5 in winter)
        assert local_dt.tzinfo is not None
        assert local_dt.tzinfo.zone == "America/New_York"
    
    def test_utc_to_local_with_timezone_aware(self, app_context):
        """Test utc_to_local with timezone-aware datetime."""
        utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
        local_dt = utc_to_local(utc_dt, "America/New_York")
        
        assert local_dt.tzinfo is not None
        assert local_dt.tzinfo.zone == "America/New_York"
    
    def test_utc_to_local_with_none(self, app_context):
        """Test utc_to_local with None input."""
        result = utc_to_local(None, "America/New_York")
        assert result is None
    
    def test_utc_to_local_different_timezone(self, app_context):
        """Test utc_to_local with different timezone."""
        utc_dt = datetime(2024, 1, 15, 12, 0, 0)
        local_dt = utc_to_local(utc_dt, "America/Los_Angeles")
        
        assert local_dt.tzinfo is not None
        assert local_dt.tzinfo.zone == "America/Los_Angeles"
    
    def test_local_to_utc_with_timezone_naive(self, app_context):
        """Test local_to_utc with timezone-naive datetime."""
        local_dt = datetime(2024, 1, 15, 7, 0, 0)  # 7 AM Eastern
        utc_dt = local_to_utc(local_dt, "America/New_York")
        
        assert utc_dt.tzinfo is not None
        assert utc_dt.tzinfo.zone == "UTC"
    
    def test_local_to_utc_with_timezone_aware(self, app_context):
        """Test local_to_utc with timezone-aware datetime."""
        eastern = pytz.timezone("America/New_York")
        local_dt = eastern.localize(datetime(2024, 1, 15, 7, 0, 0))
        utc_dt = local_to_utc(local_dt, "America/New_York")
        
        assert utc_dt.tzinfo is not None
        assert utc_dt.tzinfo.zone == "UTC"
    
    def test_local_to_utc_with_none(self, app_context):
        """Test local_to_utc with None input."""
        result = local_to_utc(None, "America/New_York")
        assert result is None
    
    def test_local_to_utc_different_timezone(self, app_context):
        """Test local_to_utc with different timezone."""
        local_dt = datetime(2024, 1, 15, 4, 0, 0)  # 4 AM Pacific
        utc_dt = local_to_utc(local_dt, "America/Los_Angeles")
        
        assert utc_dt.tzinfo is not None
        assert utc_dt.tzinfo.zone == "UTC"
    
    def test_timezone_conversion_roundtrip(self, app_context):
        """Test that timezone conversions are reversible."""
        original_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
        
        # Convert to local and back
        local_dt = utc_to_local(original_utc, "America/New_York")
        back_to_utc = local_to_utc(local_dt, "America/New_York")
        
        # Should be the same time (within microseconds)
        assert abs((back_to_utc - original_utc).total_seconds()) < 1


class TestAppConfiguration:
    """Test app configuration and context processors."""
    
    def test_app_configuration(self, app_context):
        """Test basic app configuration."""
        assert app.config["TESTING"] is True
        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
        assert app.config["WTF_CSRF_ENABLED"] is False
        assert app.config["SESSION_SECRET"] == "test-secret"
    
    def test_app_context_processor(self, app_context):
        """Test that current_year is available in templates."""
        with app.test_request_context():
            # Get the context processor function
            context_funcs = app.context_processor(lambda: {})
            
            # Check that inject_current_year is registered
            assert any(func.__name__ == 'inject_current_year' 
                      for func in app.template_context_processors[None])
    
    def test_database_initialization(self, app_context):
        """Test that database tables are created."""
        # Check that tables exist by importing models
        from models import User, Show, ShowInstance, Signup
        
        # These should not raise exceptions
        assert User.__tablename__ == 'users'
        assert Show.__tablename__ == 'show'
        assert ShowInstance.__tablename__ == 'show_instance'
        assert Signup.__tablename__ == 'signup'
    
    def test_proxy_fix_middleware(self, app_context):
        """Test that ProxyFix middleware is configured."""
        from werkzeug.middleware.proxy_fix import ProxyFix
        
        # Check that the middleware is applied
        assert isinstance(app.wsgi_app, ProxyFix)
    
    def test_login_manager_configuration(self, app_context):
        """Test that login manager is properly configured."""
        from flask_login import LoginManager
        
        # Check that login manager is initialized
        assert hasattr(app, 'login_manager')
        assert isinstance(app.login_manager, LoginManager)
        assert app.login_manager.login_view == "replit_auth.login"
    
    def test_session_configuration(self, app_context):
        """Test session configuration."""
        assert app.config.get('SESSION_COOKIE_SAMESITE') == 'Lax'
        assert app.config.get('SESSION_COOKIE_SECURE') is False
        assert app.config.get('SESSION_COOKIE_HTTPONLY') is True
    
    def test_database_engine_options(self, app_context):
        """Test database engine options."""
        expected_options = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        
        assert app.config["SQLALCHEMY_ENGINE_OPTIONS"] == expected_options
        assert app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] is False


class TestAppImports:
    """Test that all required modules are properly imported."""
    
    def test_models_import(self, app_context):
        """Test that models are properly imported."""
        from models import User, Show, ShowInstance, Signup, OAuth
        
        # These should not raise ImportError
        assert User is not None
        assert Show is not None
        assert ShowInstance is not None
        assert Signup is not None
        assert OAuth is not None
    
    def test_forms_import(self, app_context):
        """Test that forms are properly imported."""
        from forms import EventForm, SignupForm, CancellationForm
        
        # These should not raise ImportError
        assert EventForm is not None
        assert SignupForm is not None
        assert CancellationForm is not None
    
    def test_routes_import(self, app_context):
        """Test that routes module is properly imported."""
        # This should not raise ImportError
        import routes
        assert routes is not None
    
    def test_replit_auth_import(self, app_context):
        """Test that replit_auth module is properly imported."""
        from replit_auth import make_replit_blueprint
        
        # This should not raise ImportError
        assert make_replit_blueprint is not None


class TestErrorHandling:
    """Test error handling in utility functions."""
    
    def test_utc_to_local_with_invalid_timezone(self, app_context):
        """Test utc_to_local with invalid timezone."""
        utc_dt = datetime(2024, 1, 15, 12, 0, 0)
        
        with pytest.raises(pytz.exceptions.UnknownTimeZoneError):
            utc_to_local(utc_dt, "Invalid/Timezone")
    
    def test_local_to_utc_with_invalid_timezone(self, app_context):
        """Test local_to_utc with invalid timezone."""
        local_dt = datetime(2024, 1, 15, 7, 0, 0)
        
        with pytest.raises(pytz.exceptions.UnknownTimeZoneError):
            local_to_utc(local_dt, "Invalid/Timezone")
    
    def test_timezone_functions_with_edge_cases(self, app_context):
        """Test timezone functions with edge cases."""
        # Test with leap year
        leap_year_dt = datetime(2024, 2, 29, 12, 0, 0)
        result = utc_to_local(leap_year_dt, "America/New_York")
        assert result is not None
        
        # Test with daylight saving time transition
        dst_dt = datetime(2024, 3, 10, 7, 0, 0)  # DST starts
        result = utc_to_local(dst_dt, "America/New_York")
        assert result is not None