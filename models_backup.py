from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_comedian = db.Column(db.Boolean, default=True, nullable=False)
    is_host = db.Column(db.Boolean, default=False, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    events = db.relationship("Event", backref="host", lazy=True)
    signups = db.relationship("Signup", backref="comedian", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        import secrets

        self.email_verification_token = secrets.token_urlsafe(32)
        return self.email_verification_token

    def verify_email(self):
        self.email_verified = True
        self.email_verification_token = None

    def become_host(self):
        """Make this user a host when they create their first event"""
        self.is_host = True

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def primary_role(self):
        """Return the primary role for display purposes"""
        if self.is_host and self.is_comedian:
            return "Host & Comedian"
        elif self.is_host:
            return "Host"
        else:
            return "Comedian"


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    venue = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=True)
    description = db.Column(db.Text)
    max_signups = db.Column(db.Integer, default=20)
    signup_deadline_hours = db.Column(db.Integer, default=2)  # Hours before event
    host_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    signups = db.relationship(
        "Signup", backref="event", lazy=True, cascade="all, delete-orphan"
    )
    cancellations = db.relationship(
        "EventCancellation", backref="event", lazy=True, cascade="all, delete-orphan"
    )


class Signup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comedian_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    signup_time = db.Column(db.DateTime, default=datetime.utcnow)
    position = db.Column(db.Integer)  # Position in lineup
    performed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint(
            "comedian_id", "event_id", "event_date", name="unique_signup"
        ),
    )


class EventCancellation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    cancelled_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("event_id", "cancelled_date", name="unique_cancellation"),
    )
