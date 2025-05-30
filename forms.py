from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, PasswordField, TimeField, IntegerField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Regexp
from models import User, Show
import re

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email(message='Please enter a valid email address.'),
        Regexp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', 
               message='Please enter a valid email address.')
    ])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        # Additional email validation
        email_value = email.data.lower().strip()
        
        # Check for common invalid patterns
        if '..' in email_value or email_value.startswith('.') or email_value.endswith('.'):
            raise ValidationError('Please enter a valid email address.')
        
        # Check if email already exists
        user = User.query.filter_by(email=email_value).first()
        if user:
            raise ValidationError('Please use a different email address.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class EventForm(FlaskForm):
    name = StringField('Event Name', validators=[DataRequired(), Length(max=100)])
    venue = StringField('Venue', validators=[DataRequired(), Length(max=100)])
    address = StringField('Address', validators=[DataRequired(), Length(max=200)])
    day_of_week = SelectField('Day of Week', choices=[
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday')
    ], validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    description = TextAreaField('Description')
    max_signups = IntegerField('Maximum Signups', validators=[DataRequired(), NumberRange(min=1, max=50)])
    signup_deadline_hours = IntegerField('Signup Deadline (hours before)', validators=[DataRequired(), NumberRange(min=0, max=72)])

class SignupForm(FlaskForm):
    notes = TextAreaField('Notes (Optional)', validators=[Length(max=500)])

class CancellationForm(FlaskForm):
    cancelled_date = DateField('Date to Cancel', validators=[DataRequired()])
    reason = StringField('Reason (Optional)', validators=[Length(max=200)])
