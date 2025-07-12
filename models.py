import secrets
from datetime import date, datetime, time, timedelta

from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import UniqueConstraint

from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    
    # Keep legacy fields for backward compatibility
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    email_verified = db.Column(db.Boolean, default=True, nullable=False)
    email_verification_token = db.Column(db.String(100), unique=True, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owned_shows = db.relationship(
        "Show", backref="owner", lazy=True, foreign_keys="Show.owner_id"
    )
    show_runner_roles = db.relationship(
        "ShowRunner", backref="user", lazy=True, foreign_keys="ShowRunner.user_id"
    )
    show_host_roles = db.relationship(
        "ShowHost", backref="user", lazy=True, foreign_keys="ShowHost.user_id"
    )
    signups = db.relationship("Signup", backref="comedian", lazy=True)
    instance_host_roles = db.relationship("ShowInstanceHost", backref="user", lazy=True)

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        """Generate email verification token"""
        self.email_verification_token = secrets.token_urlsafe(32)
        return self.email_verification_token

    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.email_verification_token = None

    @property
    def full_name(self):
        """Return full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        elif self.username:
            return self.username
        else:
            return self.email or f"User {self.id}"

    def get_show_role(self, show):
        """Get user's highest role for a specific show"""
        if show.owner_id == self.id:
            return "owner"

        runner = ShowRunner.query.filter_by(show_id=show.id, user_id=self.id).first()
        if runner:
            return "runner"

        host = ShowHost.query.filter_by(show_id=show.id, user_id=self.id).first()
        if host:
            return "host"

        return "comedian"

    def can_edit_show(self, show):
        """Check if user can edit show settings"""
        return self.get_show_role(show) in ["owner", "runner"]

    def can_manage_lineup(self, show):
        """Check if user can manage show lineup"""
        return self.get_show_role(show) in ["owner", "runner", "host"]


# OAuth table is mandatory for Replit Auth
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)


class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    venue = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    timezone = db.Column(db.String(50), nullable=False, default="America/New_York")
    description = db.Column(db.Text)

    # Show timing and scheduling
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=True)
    repeat_cadence = db.Column(
        db.String(20), default="weekly"
    )  # weekly, bi-weekly, monthly, custom
    custom_repeat_days = db.Column(db.Integer, nullable=True)  # For custom cadence

    # Show lifecycle
    started_date = db.Column(db.Date, nullable=False, default=date.today)
    ended_date = db.Column(
        db.Date, nullable=True
    )  # When show was permanently cancelled
    is_deleted = db.Column(db.Boolean, default=False)

    # Show settings
    max_signups = db.Column(db.Integer, default=20)
    signups_open = db.Column(db.Integer, default=2880)  # Minutes before show when signups open (default: 2 days)
    signups_closed = db.Column(db.Integer, default=0)  # Minutes before show when signups close (default: at show start)
    signup_window_before_days = db.Column(
        db.Integer, default=14
    )  # How early can comedians sign up (DEPRECATED - use signups_open)
    signup_window_after_hours = db.Column(
        db.Integer, default=2
    )  # How late can comedians sign up (DEPRECATED - use signups_closed)

    # Ownership
    owner_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    default_host_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=True)

    # Display settings
    show_host_info = db.Column(db.Boolean, default=True)  # Show host info publicly
    show_owner_info = db.Column(db.Boolean, default=False)  # Show owner info publicly

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    default_host = db.relationship("User", foreign_keys=[default_host_id])
    runners = db.relationship(
        "ShowRunner", backref="show", lazy=True, cascade="all, delete-orphan"
    )
    hosts = db.relationship(
        "ShowHost", backref="show", lazy=True, cascade="all, delete-orphan"
    )
    instances = db.relationship(
        "ShowInstance", backref="show", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def is_active(self):
        """Show is active if not deleted and not permanently ended"""
        return not self.is_deleted and self.ended_date is None

    def soft_delete(self):
        """Mark show as deleted but keep in database"""
        self.is_deleted = True
        self.ended_date = date.today()

    def undelete(self):
        """Restore a deleted show"""
        self.is_deleted = False
        self.ended_date = None

    def get_signup_open_datetime(self, instance_date):
        """Calculate when signups open for a specific instance"""
        from datetime import datetime, timedelta, timezone
        from app import utc_to_local
        
        # Combine instance date with show start time in UTC
        show_datetime_utc = datetime.combine(instance_date, self.start_time)
        
        # Convert to timezone-aware datetime (times are stored in UTC)
        show_datetime_utc = show_datetime_utc.replace(tzinfo=timezone.utc)
        
        # Subtract signups_open minutes
        signup_open_utc = show_datetime_utc - timedelta(minutes=self.signups_open)
        
        # Convert back to local timezone for display
        return utc_to_local(signup_open_utc, self.timezone)
    
    def get_signup_closed_datetime(self, instance_date):
        """Calculate when signups close for a specific instance"""
        from datetime import datetime, timedelta, timezone
        from app import utc_to_local
        
        # Combine instance date with show start time in UTC
        show_datetime_utc = datetime.combine(instance_date, self.start_time)
        
        # Convert to timezone-aware datetime (times are stored in UTC)
        show_datetime_utc = show_datetime_utc.replace(tzinfo=timezone.utc)
        
        # Calculate signup close time based on signups_closed value
        # Positive values: close X minutes BEFORE show start
        # Negative values: close X minutes AFTER show start  
        if self.signups_closed >= 0:
            # Normal case: close before the show
            signup_closed_utc = show_datetime_utc - timedelta(minutes=self.signups_closed)
        else:
            # Negative case: close after the show starts (add the absolute value)
            signup_closed_utc = show_datetime_utc + timedelta(minutes=abs(self.signups_closed))
        
        # Convert back to local timezone for display
        return utc_to_local(signup_closed_utc, self.timezone)
    
    @staticmethod
    def convert_time_to_minutes(value, unit):
        """Convert time value with unit to minutes"""
        if unit == "minutes":
            return value
        elif unit == "hours":
            return value * 60
        elif unit == "days":
            return value * 60 * 24
        elif unit == "weeks":
            return value * 60 * 24 * 7
        elif unit == "months":
            return value * 60 * 24 * 30  # Approximate 30 days per month
        else:
            return value
    
    @staticmethod
    def convert_minutes_to_time_unit(minutes, preferred_unit="days"):
        """Convert minutes back to most appropriate time unit for display"""
        if minutes == 0:
            return 0, "minutes"
        
        # Try to find the largest unit that divides evenly
        if minutes % (30 * 24 * 60) == 0:
            return minutes // (30 * 24 * 60), "months"
        elif minutes % (7 * 24 * 60) == 0:
            return minutes // (7 * 24 * 60), "weeks"
        elif minutes % (24 * 60) == 0:
            return minutes // (24 * 60), "days"
        elif minutes % 60 == 0:
            return minutes // 60, "hours"
        else:
            return minutes, "minutes"

    def get_next_instance_date(self, from_date=None):
        """Calculate next show instance date based on repeat cadence"""
        if from_date is None:
            from_date = date.today()

        # Find the next occurrence based on day of week and cadence
        days_ahead = 0
        while True:
            check_date = from_date + timedelta(days=days_ahead)
            if check_date.strftime("%A") == self.day_of_week:
                if self.repeat_cadence == "weekly":
                    return check_date
                elif self.repeat_cadence == "bi-weekly":
                    # Check if it's the right week
                    weeks_since_start = (check_date - self.started_date).days // 7
                    if weeks_since_start % 2 == 0:
                        return check_date
                elif self.repeat_cadence == "monthly":
                    # Find the right week of the month
                    start_week = (self.started_date.day - 1) // 7
                    current_week = (check_date.day - 1) // 7
                    if start_week == current_week:
                        return check_date
                elif self.repeat_cadence == "custom" and self.custom_repeat_days:
                    days_since_start = (check_date - self.started_date).days
                    if days_since_start % self.custom_repeat_days == 0:
                        return check_date

            days_ahead += 1
            if days_ahead > 365:  # Safety check
                return None


class ShowRunner(db.Model):
    """Show runners have admin-level permissions for a show"""

    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("show_id", "user_id", name="unique_show_runner"),
    )


class ShowHost(db.Model):
    """Show hosts can manage lineups but not show settings"""

    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("show_id", "user_id", name="unique_show_host"),
    )


class ShowInstance(db.Model):
    """A specific occurrence of a show on a particular date"""

    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
    instance_date = db.Column(db.Date, nullable=False)

    # Instance-specific overrides
    is_cancelled = db.Column(db.Boolean, default=False)
    cancellation_reason = db.Column(db.String(200), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # Override show settings for this instance if needed
    max_signups_override = db.Column(db.Integer, nullable=True)
    start_time_override = db.Column(db.Time, nullable=True)
    end_time_override = db.Column(db.Time, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    signups = db.relationship(
        "Signup", backref="show_instance", lazy=True, cascade="all, delete-orphan"
    )
    hosts = db.relationship(
        "ShowInstanceHost",
        backref="show_instance",
        lazy=True,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("show_id", "instance_date", name="unique_show_instance"),
    )

    @property
    def max_signups(self):
        """Get max signups for this instance (override or show default)"""
        return self.max_signups_override or self.show.max_signups

    @property
    def start_time(self):
        """Get start time for this instance (override or show default)"""
        return self.start_time_override or self.show.start_time

    @property
    def end_time(self):
        """Get end time for this instance (override or show default)"""
        return self.end_time_override or self.show.end_time

    def cancel(self, reason=None):
        """Cancel this show instance"""
        self.is_cancelled = True
        self.cancellation_reason = reason
        self.cancelled_at = datetime.utcnow()

    def uncancel(self):
        """Restore a cancelled show instance"""
        self.is_cancelled = False
        self.cancellation_reason = None
        self.cancelled_at = None

    def get_hosts(self):
        """Get hosts for this instance (instance-specific or default)"""
        instance_hosts = [host.user for host in self.hosts]
        if instance_hosts:
            return instance_hosts
        elif self.show.default_host:
            return [self.show.default_host]
        else:
            return []

    def get_host_names(self):
        """Get formatted host names for display"""
        hosts = self.get_hosts()
        if not hosts:
            return "TBD"
        elif len(hosts) == 1:
            return hosts[0].full_name
        else:
            return ", ".join([host.full_name for host in hosts])
    
    def is_signup_open(self):
        """Check if signups are currently open for this instance"""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        signup_open = self.show.get_signup_open_datetime(self.instance_date)
        signup_closed = self.show.get_signup_closed_datetime(self.instance_date)
        
        # Convert to UTC for comparison
        from app import local_to_utc
        signup_open_utc = local_to_utc(signup_open, self.show.timezone)
        signup_closed_utc = local_to_utc(signup_closed, self.show.timezone)
        
        return signup_open_utc <= now <= signup_closed_utc
    
    def get_signup_status(self):
        """Get signup status with descriptive message"""
        from datetime import datetime, timezone
        from app import local_to_utc
        
        now = datetime.now(timezone.utc)
        signup_open = self.show.get_signup_open_datetime(self.instance_date)
        signup_closed = self.show.get_signup_closed_datetime(self.instance_date)
        
        # Convert to UTC for comparison
        signup_open_utc = local_to_utc(signup_open, self.show.timezone)
        signup_closed_utc = local_to_utc(signup_closed, self.show.timezone)
        
        if now < signup_open_utc:
            return {
                'status': 'not_open',
                'message': f"Signups open {signup_open.strftime('%m/%d/%y at %I:%M %p')}",
                'can_signup': False
            }
        elif now > signup_closed_utc:
            return {
                'status': 'closed',
                'message': "Signups are closed",
                'can_signup': False
            }
        else:
            return {
                'status': 'open',
                'message': "Signups are open",
                'can_signup': True
            }


class ShowInstanceHost(db.Model):
    """Specific hosts designated for a particular show instance"""

    id = db.Column(db.Integer, primary_key=True)
    show_instance_id = db.Column(
        db.Integer, db.ForeignKey("show_instance.id"), nullable=False
    )
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("show_instance_id", "user_id", name="unique_instance_host"),
    )


class Signup(db.Model):
    """Comedian signup for a specific show instance"""

    id = db.Column(db.Integer, primary_key=True)
    comedian_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    show_instance_id = db.Column(
        db.Integer, db.ForeignKey("show_instance.id"), nullable=False
    )
    signup_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Lineup management
    position = db.Column(
        db.Integer, nullable=True
    )  # Position in lineup (1, 2, 3, etc.)
    is_present = db.Column(
        db.Boolean, nullable=True
    )  # Marked present/absent on show day
    performed = db.Column(db.Boolean, default=False)  # Actually performed
    notes = db.Column(db.Text, nullable=True)  # Comedian's notes or host notes

    __table_args__ = (
        db.UniqueConstraint("comedian_id", "show_instance_id", name="unique_signup"),
    )

    @property
    def show(self):
        """Get the show this signup is for"""
        return self.show_instance.show
