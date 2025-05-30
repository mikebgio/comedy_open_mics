import os
from flask import url_for, current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_verification_email(user):
    """Send email verification to user"""
    if not os.environ.get('SENDGRID_API_KEY'):
        current_app.logger.warning("SENDGRID_API_KEY not set - email verification disabled")
        return False
    
    try:
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
        
        message = Mail(
            from_email='noreply@comedyopenmic.com',  # This should be a verified sender
            to_emails=user.email,
            subject='Verify your email - Comedy Open Mic Manager',
            html_content=html_content
        )
        
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        
        current_app.logger.info(f"Verification email sent to {user.email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        return False

def send_welcome_email(user):
    """Send welcome email after verification"""
    if not os.environ.get('SENDGRID_API_KEY'):
        return False
        
    try:
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
        
        message = Mail(
            from_email='noreply@comedyopenmic.com',
            to_emails=user.email,
            subject='Welcome to Comedy Open Mic Manager!',
            html_content=html_content
        )
        
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email: {str(e)}")
        return False