import os
import boto3
from botocore.exceptions import ClientError
from flask import url_for, current_app

def send_verification_email(user):
    """Send email verification to user using AWS SES"""
    # Check for AWS credentials
    if not (os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY')):
        current_app.logger.warning("AWS credentials not set - email verification disabled")
        return False
    
    try:
        # Create SES client
        ses_client = boto3.client(
            'ses',
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        
        verification_url = url_for('verify_email', 
                                 token=user.email_verification_token, 
                                 _external=True)
        
        html_content = f"""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <h2 style="color: #333;">Welcome to Comedy Open Mic Manager!</h2>
            <p>Hi {user.first_name},</p>
            <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background-color: #007bff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p><a href="{verification_url}">{verification_url}</a></p>
            <p>This link will expire in 24 hours for security reasons.</p>
            <p>If you didn't sign up for this account, you can safely ignore this email.</p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
                Comedy Open Mic Manager - Connecting comedians and hosts
            </p>
        </div>
        """
        
        text_content = f"""
        Welcome to Comedy Open Mic Manager!
        
        Hi {user.first_name},
        
        Thanks for signing up! Please verify your email address by visiting this link:
        {verification_url}
        
        This link will expire in 24 hours for security reasons.
        
        If you didn't sign up for this account, you can safely ignore this email.
        
        Comedy Open Mic Manager - Connecting comedians and hosts
        """
        
        # Send email using SES
        response = ses_client.send_email(
            Source=os.environ.get('SES_FROM_EMAIL', 'noreply@comedyopenmic.com'),
            Destination={'ToAddresses': [user.email]},
            Message={
                'Subject': {'Data': 'Verify your email - Comedy Open Mic Manager'},
                'Body': {
                    'Text': {'Data': text_content},
                    'Html': {'Data': html_content}
                }
            }
        )
        
        current_app.logger.info(f"Verification email sent to {user.email} via AWS SES")
        return True
        
    except ClientError as e:
        current_app.logger.error(f"AWS SES error: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        return False

def send_welcome_email(user):
    """Send welcome email after verification using AWS SES"""
    if not (os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY')):
        return False
        
    try:
        # Create SES client
        ses_client = boto3.client(
            'ses',
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        
        html_content = f"""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <h2 style="color: #333;">Welcome to Comedy Open Mic Manager!</h2>
            <p>Hi {user.first_name},</p>
            <p>Your email has been verified successfully! You're now ready to:</p>
            <ul>
                <li>Sign up for comedy open mic events</li>
                <li>View live lineups and track your spot</li>
                <li>Create and manage your own open mic events</li>
            </ul>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{url_for('dashboard', _external=True)}" 
                   style="background-color: #28a745; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Go to Dashboard
                </a>
            </div>
            <p>Happy performing!</p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
                Comedy Open Mic Manager - Connecting comedians and hosts
            </p>
        </div>
        """
        
        text_content = f"""
        Welcome to Comedy Open Mic Manager!
        
        Hi {user.first_name},
        
        Your email has been verified successfully! You're now ready to:
        - Sign up for comedy open mic events
        - View live lineups and track your spot
        - Create and manage your own open mic events
        
        Visit your dashboard: {url_for('dashboard', _external=True)}
        
        Happy performing!
        
        Comedy Open Mic Manager - Connecting comedians and hosts
        """
        
        # Send email using SES
        response = ses_client.send_email(
            Source=os.environ.get('SES_FROM_EMAIL', 'noreply@comedyopenmic.com'),
            Destination={'ToAddresses': [user.email]},
            Message={
                'Subject': {'Data': 'Welcome to Comedy Open Mic Manager!'},
                'Body': {
                    'Text': {'Data': text_content},
                    'Html': {'Data': html_content}
                }
            }
        )
        
        current_app.logger.info(f"Welcome email sent to {user.email} via AWS SES")
        return True
        
    except ClientError as e:
        current_app.logger.error(f"AWS SES error: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email: {str(e)}")
        return False