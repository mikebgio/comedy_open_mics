#!/usr/bin/env python3
"""
Unit tests for email_service.py
"""
import pytest

pytestmark = pytest.mark.unit
import tempfile
import os
from unittest.mock import patch, MagicMock, Mock
import boto3
from botocore.exceptions import ClientError

from app import app, db
from models import User
from email_service import send_verification_email, send_welcome_email


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
        email_verification_token="test-token-123"
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestSendVerificationEmail:
    """Test send_verification_email function."""
    
    @patch('email_service.boto3.client')
    def test_send_verification_email_success(self, mock_boto3_client, app_context, sample_user):
        """Test successful verification email sending."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {
            'MessageId': 'test-message-id-123'
        }
        
        # Call function
        result = send_verification_email(sample_user)
        
        # Verify SES client was called correctly
        mock_boto3_client.assert_called_once_with('ses')
        mock_ses.send_email.assert_called_once()
        
        # Verify call arguments
        call_args = mock_ses.send_email.call_args[1]
        assert call_args['Source'] == 'noreply@comedyopenmic.com'
        assert sample_user.email in call_args['Destination']['ToAddresses']
        assert 'Email Verification' in call_args['Message']['Subject']['Data']
        assert sample_user.email_verification_token in call_args['Message']['Body']['Html']['Data']
        
        # Verify return value
        assert result is True
    
    @patch('email_service.boto3.client')
    def test_send_verification_email_client_error(self, mock_boto3_client, app_context, sample_user):
        """Test verification email sending with SES client error."""
        # Mock SES client with error
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            error_response={'Error': {'Code': 'MessageRejected', 'Message': 'Email rejected'}},
            operation_name='SendEmail'
        )
        
        # Call function
        result = send_verification_email(sample_user)
        
        # Verify error was handled
        assert result is False
    
    @patch('email_service.boto3.client')
    def test_send_verification_email_general_exception(self, mock_boto3_client, app_context, sample_user):
        """Test verification email sending with general exception."""
        # Mock SES client with exception
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.side_effect = Exception("Network error")
        
        # Call function
        result = send_verification_email(sample_user)
        
        # Verify exception was handled
        assert result is False
    
    def test_send_verification_email_no_token(self, app_context):
        """Test verification email sending without verification token."""
        user_without_token = User(
            id="test-user-456",
            email="notoken@example.com",
            first_name="No",
            last_name="Token",
            username="notoken"
        )
        db.session.add(user_without_token)
        db.session.commit()
        
        # Call function
        result = send_verification_email(user_without_token)
        
        # Should fail without token
        assert result is False
    
    def test_send_verification_email_no_email(self, app_context):
        """Test verification email sending without email address."""
        user_without_email = User(
            id="test-user-789",
            email=None,
            first_name="No",
            last_name="Email",
            username="noemail",
            email_verification_token="test-token-456"
        )
        db.session.add(user_without_email)
        db.session.commit()
        
        # Call function
        result = send_verification_email(user_without_email)
        
        # Should fail without email
        assert result is False
    
    @patch('email_service.boto3.client')
    def test_send_verification_email_email_content(self, mock_boto3_client, app_context, sample_user):
        """Test verification email content."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        
        # Call function
        send_verification_email(sample_user)
        
        # Get the email content
        call_args = mock_ses.send_email.call_args[1]
        html_body = call_args['Message']['Body']['Html']['Data']
        text_body = call_args['Message']['Body']['Text']['Data']
        
        # Verify content includes expected elements
        assert 'Test User' in html_body
        assert 'test-token-123' in html_body
        assert 'verify your email' in html_body.lower()
        assert 'Test User' in text_body
        assert 'test-token-123' in text_body
        assert 'verify your email' in text_body.lower()


class TestSendWelcomeEmail:
    """Test send_welcome_email function."""
    
    @patch('email_service.boto3.client')
    def test_send_welcome_email_success(self, mock_boto3_client, app_context, sample_user):
        """Test successful welcome email sending."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {
            'MessageId': 'test-message-id-456'
        }
        
        # Call function
        result = send_welcome_email(sample_user)
        
        # Verify SES client was called correctly
        mock_boto3_client.assert_called_once_with('ses')
        mock_ses.send_email.assert_called_once()
        
        # Verify call arguments
        call_args = mock_ses.send_email.call_args[1]
        assert call_args['Source'] == 'noreply@comedyopenmic.com'
        assert sample_user.email in call_args['Destination']['ToAddresses']
        assert 'Welcome to Comedy Open Mic Manager' in call_args['Message']['Subject']['Data']
        
        # Verify return value
        assert result is True
    
    @patch('email_service.boto3.client')
    def test_send_welcome_email_client_error(self, mock_boto3_client, app_context, sample_user):
        """Test welcome email sending with SES client error."""
        # Mock SES client with error
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            error_response={'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            operation_name='SendEmail'
        )
        
        # Call function
        result = send_welcome_email(sample_user)
        
        # Verify error was handled
        assert result is False
    
    @patch('email_service.boto3.client')
    def test_send_welcome_email_general_exception(self, mock_boto3_client, app_context, sample_user):
        """Test welcome email sending with general exception."""
        # Mock SES client with exception
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.side_effect = Exception("Connection timeout")
        
        # Call function
        result = send_welcome_email(sample_user)
        
        # Verify exception was handled
        assert result is False
    
    def test_send_welcome_email_no_email(self, app_context):
        """Test welcome email sending without email address."""
        user_without_email = User(
            id="test-user-000",
            email=None,
            first_name="No",
            last_name="Email",
            username="noemail"
        )
        db.session.add(user_without_email)
        db.session.commit()
        
        # Call function
        result = send_welcome_email(user_without_email)
        
        # Should fail without email
        assert result is False
    
    @patch('email_service.boto3.client')
    def test_send_welcome_email_content(self, mock_boto3_client, app_context, sample_user):
        """Test welcome email content."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        
        # Call function
        send_welcome_email(sample_user)
        
        # Get the email content
        call_args = mock_ses.send_email.call_args[1]
        html_body = call_args['Message']['Body']['Html']['Data']
        text_body = call_args['Message']['Body']['Text']['Data']
        
        # Verify content includes expected elements
        assert 'Test User' in html_body
        assert 'welcome' in html_body.lower()
        assert 'comedy open mic' in html_body.lower()
        assert 'Test User' in text_body
        assert 'welcome' in text_body.lower()
        assert 'comedy open mic' in text_body.lower()
    
    @patch('email_service.boto3.client')
    def test_send_welcome_email_with_username_only(self, mock_boto3_client, app_context):
        """Test welcome email with user who has only username."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        
        # Create user with only username
        user_username_only = User(
            id="test-user-username",
            email="username@example.com",
            first_name="",
            last_name="",
            username="onlyusername"
        )
        db.session.add(user_username_only)
        db.session.commit()
        
        # Call function
        send_welcome_email(user_username_only)
        
        # Get the email content
        call_args = mock_ses.send_email.call_args[1]
        html_body = call_args['Message']['Body']['Html']['Data']
        
        # Should use username when name is not available
        assert 'onlyusername' in html_body


class TestEmailUtilities:
    """Test email utility functions and edge cases."""
    
    @patch('email_service.boto3.client')
    def test_boto3_client_creation(self, mock_boto3_client, app_context, sample_user):
        """Test that boto3 client is created correctly."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-id'}
        
        # Call function
        send_verification_email(sample_user)
        
        # Verify boto3 client was called with correct service
        mock_boto3_client.assert_called_once_with('ses')
    
    @patch('email_service.boto3.client')
    def test_email_formatting(self, mock_boto3_client, app_context):
        """Test email formatting with different user scenarios."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-id'}
        
        # Test with user with special characters in name
        special_user = User(
            id="special-user",
            email="special@example.com",
            first_name="José",
            last_name="O'Brien",
            username="jose_obrien",
            email_verification_token="special-token"
        )
        db.session.add(special_user)
        db.session.commit()
        
        # Call function
        send_verification_email(special_user)
        
        # Verify special characters are handled
        call_args = mock_ses.send_email.call_args[1]
        html_body = call_args['Message']['Body']['Html']['Data']
        assert "José O'Brien" in html_body
    
    @patch('email_service.boto3.client')
    def test_email_encoding(self, mock_boto3_client, app_context):
        """Test email encoding with unicode characters."""
        # Mock SES client
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-id'}
        
        # Test with unicode characters
        unicode_user = User(
            id="unicode-user",
            email="unicode@example.com",
            first_name="测试",
            last_name="用户",
            username="test_unicode",
            email_verification_token="unicode-token"
        )
        db.session.add(unicode_user)
        db.session.commit()
        
        # Call function - should not raise encoding errors
        result = send_verification_email(unicode_user)
        
        # Should succeed
        assert result is True
    
    @patch('email_service.boto3.client')  
    def test_email_rate_limiting_handling(self, mock_boto3_client, app_context, sample_user):
        """Test handling of rate limiting errors."""
        # Mock SES client with rate limiting error
        mock_ses = Mock()
        mock_boto3_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            error_response={'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            operation_name='SendEmail'
        )
        
        # Call function
        result = send_verification_email(sample_user)
        
        # Should handle rate limiting gracefully
        assert result is False