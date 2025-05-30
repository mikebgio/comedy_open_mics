from datetime import datetime, date, time, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    owned_shows = db.relationship('Show', backref='owner', lazy=True, foreign_keys='Show.owner_id')
    show_runner_roles = db.relationship('ShowRunner', backref='user', lazy=True, foreign_keys='ShowRunner.user_id')
    show_host_roles = db.relationship('ShowHost', backref='user', lazy=True, foreign_keys='ShowHost.user_id')
    signups = db.relationship('Signup', backref='comedian', lazy=True)
    instance_host_roles = db.relationship('ShowInstanceHost', backref='user', lazy=True)
    
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
        return f"{self.first_name} {self.last_name}"
    
    def get_show_role(self, show):
        """Get user's highest role for a specific show"""
        if show.owner_id == self.id:
            return 'owner'
        
        runner = ShowRunner.query.filter_by(show_id=show.id, user_id=self.id).first()
        if runner:
            return 'runner'
        
        host = ShowHost.query.filter_by(show_id=show.id, user_id=self.id).first()
        if host:
            return 'host'
        
        return 'comedian'
    
    def can_edit_show(self, show):
        """Check if user can edit show settings"""
        return self.get_show_role(show) in ['owner', 'runner']
    
    def can_manage_lineup(self, show):
        """Check if user can manage show lineup"""
        return self.get_show_role(show) in ['owner', 'runner', 'host']

class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    venue = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Show timing and scheduling
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=True)
    repeat_cadence = db.Column(db.String(20), default='weekly')  # weekly, bi-weekly, monthly, custom
    custom_repeat_days = db.Column(db.Integer, nullable=True)  # For custom cadence
    
    # Show lifecycle
    started_date = db.Column(db.Date, nullable=False, default=date.today)
    ended_date = db.Column(db.Date, nullable=True)  # When show was permanently cancelled
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Show settings
    max_signups = db.Column(db.Integer, default=20)
    signup_window_before_days = db.Column(db.Integer, default=14)  # How early can comedians sign up
    signup_window_after_hours = db.Column(db.Integer, default=2)  # How late can comedians sign up
    
    # Ownership
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    default_host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    default_host = db.relationship('User', foreign_keys=[default_host_id])
    runners = db.relationship('ShowRunner', backref='show', lazy=True, cascade='all, delete-orphan')
    hosts = db.relationship('ShowHost', backref='show', lazy=True, cascade='all, delete-orphan')
    instances = db.relationship('ShowInstance', backref='show', lazy=True, cascade='all, delete-orphan')
    
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
    
    def get_next_instance_date(self, from_date=None):
        """Calculate next show instance date based on repeat cadence"""
        if from_date is None:
            from_date = date.today()
        
        # Find the next occurrence based on day of week and cadence
        days_ahead = 0
        while True:
            check_date = from_date + timedelta(days=days_ahead)
            if check_date.strftime('%A') == self.day_of_week:
                if self.repeat_cadence == 'weekly':
                    return check_date
                elif self.repeat_cadence == 'bi-weekly':
                    # Check if it's the right week
                    weeks_since_start = (check_date - self.started_date).days // 7
                    if weeks_since_start % 2 == 0:
                        return check_date
                elif self.repeat_cadence == 'monthly':
                    # Find the right week of the month
                    start_week = (self.started_date.day - 1) // 7
                    current_week = (check_date.day - 1) // 7
                    if start_week == current_week:
                        return check_date
                elif self.repeat_cadence == 'custom' and self.custom_repeat_days:
                    days_since_start = (check_date - self.started_date).days
                    if days_since_start % self.custom_repeat_days == 0:
                        return check_date
            
            days_ahead += 1
            if days_ahead > 365:  # Safety check
                return None

class ShowRunner(db.Model):
    """Show runners have admin-level permissions for a show"""
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('show_id', 'user_id', name='unique_show_runner'),)

class ShowHost(db.Model):
    """Show hosts can manage lineups but not show settings"""
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('show_id', 'user_id', name='unique_show_host'),)

class ShowInstance(db.Model):
    """A specific occurrence of a show on a particular date"""
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'), nullable=False)
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
    signups = db.relationship('Signup', backref='show_instance', lazy=True, cascade='all, delete-orphan')
    hosts = db.relationship('ShowInstanceHost', backref='show_instance', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('show_id', 'instance_date', name='unique_show_instance'),)
    
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

class ShowInstanceHost(db.Model):
    """Specific hosts designated for a particular show instance"""
    id = db.Column(db.Integer, primary_key=True)
    show_instance_id = db.Column(db.Integer, db.ForeignKey('show_instance.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('show_instance_id', 'user_id', name='unique_instance_host'),)

class Signup(db.Model):
    """Comedian signup for a specific show instance"""
    id = db.Column(db.Integer, primary_key=True)
    comedian_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    show_instance_id = db.Column(db.Integer, db.ForeignKey('show_instance.id'), nullable=False)
    signup_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Lineup management
    position = db.Column(db.Integer, nullable=True)  # Position in lineup (1, 2, 3, etc.)
    is_present = db.Column(db.Boolean, nullable=True)  # Marked present/absent on show day
    performed = db.Column(db.Boolean, default=False)  # Actually performed
    notes = db.Column(db.Text, nullable=True)  # Comedian's notes or host notes
    
    __table_args__ = (db.UniqueConstraint('comedian_id', 'show_instance_id', name='unique_signup'),)
    
    @property
    def show(self):
        """Get the show this signup is for"""
        return self.show_instance.show