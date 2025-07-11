import re

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)

from models import Show, User


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=4, max=20)]
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(message="Please enter a valid email address."),
            Regexp(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                message="Please enter a valid email address.",
            ),
        ],
    )
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=50)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=50)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Please use a different username.")

    def validate_email(self, email):
        # Additional email validation
        email_value = email.data.lower().strip()

        # Check for common invalid patterns
        if (
            ".." in email_value
            or email_value.startswith(".")
            or email_value.endswith(".")
        ):
            raise ValidationError("Please enter a valid email address.")

        # Check if email already exists
        user = User.query.filter_by(email=email_value).first()
        if user:
            raise ValidationError("Please use a different email address.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class EventForm(FlaskForm):
    name = StringField("Event Name", validators=[DataRequired(), Length(max=100)])
    venue = StringField("Venue", validators=[DataRequired(), Length(max=100)])
    address = StringField("Address", validators=[DataRequired(), Length(max=200)])
    day_of_week = SelectField(
        "Day of Week",
        choices=[
            ("Monday", "Monday"),
            ("Tuesday", "Tuesday"),
            ("Wednesday", "Wednesday"),
            ("Thursday", "Thursday"),
            ("Friday", "Friday"),
            ("Saturday", "Saturday"),
            ("Sunday", "Sunday"),
        ],
        validators=[DataRequired()],
    )
    start_time = StringField("Start Time", validators=[DataRequired()], render_kw={"type": "time"})
    end_time = StringField("End Time", validators=[DataRequired()], render_kw={"type": "time"})
    timezone = StringField("Timezone", default="America/New_York", render_kw={"readonly": True})
    description = TextAreaField("Description")
    max_signups = IntegerField(
        "Maximum Signups", validators=[DataRequired(), NumberRange(min=1, max=50)]
    )
    
    # New signup timing fields
    signups_open_value = IntegerField(
        "Signups Open", validators=[DataRequired(), NumberRange(min=0, max=525600)]
    )
    signups_open_unit = SelectField(
        "Unit",
        choices=[
            ("minutes", "Minutes"),
            ("hours", "Hours"),
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
        ],
        default="days",
        validators=[DataRequired()],
    )
    
    signups_closed_value = IntegerField(
        "Signups Close", validators=[DataRequired(), NumberRange(min=-1440, max=525600)]
    )
    signups_closed_unit = SelectField(
        "Unit",
        choices=[
            ("minutes", "Minutes"),
            ("hours", "Hours"),
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
        ],
        default="hours",
        validators=[DataRequired()],
    )
    
    # Deprecated field - keeping for backward compatibility
    signup_deadline_hours = IntegerField(
        "Signup Deadline (hours before)",
        validators=[DataRequired(), NumberRange(min=0, max=72)],
    )
    show_host_info = BooleanField("Show host information publicly", default=True)
    show_owner_info = BooleanField("Show owner information publicly", default=False)


class SignupForm(FlaskForm):
    notes = TextAreaField("Notes (Optional)", validators=[Length(max=500)])


class CancellationForm(FlaskForm):
    cancelled_date = DateField("Date to Cancel", validators=[DataRequired()])
    reason = StringField("Reason (Optional)", validators=[Length(max=200)])


class ShowSettingsForm(FlaskForm):
    """Form for editing show settings including host management"""

    default_host_id = SelectField("Default Host", coerce=int)
    show_host_info = BooleanField("Show host information publicly", default=True)
    show_owner_info = BooleanField("Show owner information publicly", default=False)

    def __init__(self, show=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if show:
            # Populate default host choices with users who can host this show
            from models import User

            potential_hosts = (
                User.query.all()
            )  # Could be filtered to show runners/hosts
            self.default_host_id.choices = [(0, "No default host")] + [
                (user.id, user.full_name) for user in potential_hosts
            ]


class InstanceHostForm(FlaskForm):
    """Form for assigning hosts to specific show instances"""

    host_id = SelectField("Instance Host", coerce=int, validators=[DataRequired()])

    def __init__(self, show=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if show:
            # Populate host choices with users who can host this show
            from models import User

            potential_hosts = (
                User.query.all()
            )  # Could be filtered to show runners/hosts
            self.host_id.choices = [
                (user.id, user.full_name) for user in potential_hosts
            ]
