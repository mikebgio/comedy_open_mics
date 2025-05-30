#!/usr/bin/env python3
"""
Migration script to transform existing Event-based data to the new Show/ShowInstance model
"""
import os

# Import new models
import sys
from datetime import date, datetime, timedelta

from app import app, db
from models import Event, EventCancellation
from models import Signup as OldSignup
from models import User as OldUser

sys.path.append(os.path.dirname(__file__))


def migrate_data():
    """Migrate from old Event model to new Show/ShowInstance model"""
    with app.app_context():
        print("Starting data migration...")

        # First, backup the old models data
        old_events = Event.query.all()
        old_signups = OldSignup.query.all()
        old_cancellations = EventCancellation.query.all()
        old_users = OldUser.query.all()

        print(
            f"Found {len(old_events)} events, {len(old_signups)} signups, {len(old_cancellations)} cancellations"
        )

        # Drop existing tables
        print("Dropping old tables...")
        db.drop_all()

        # Import and create new models
        # Update the models module
        import models
        from models_new import (
            Show,
            ShowHost,
            ShowInstance,
            ShowInstanceHost,
            ShowRunner,
            Signup,
            User,
        )

        models.User = User
        models.Show = Show
        models.ShowRunner = ShowRunner
        models.ShowHost = ShowHost
        models.ShowInstance = ShowInstance
        models.ShowInstanceHost = ShowInstanceHost
        models.Signup = Signup

        # Create new tables
        print("Creating new tables...")
        db.create_all()

        # Migrate users first (structure is mostly the same)
        print("Migrating users...")
        user_mapping = {}
        for old_user in old_users:
            new_user = User(
                id=old_user.id,
                username=old_user.username,
                email=old_user.email,
                password_hash=old_user.password_hash,
                first_name=old_user.first_name,
                last_name=old_user.last_name,
                email_verified=old_user.email_verified,
                email_verification_token=old_user.email_verification_token,
                created_at=old_user.created_at,
            )
            db.session.add(new_user)
            user_mapping[old_user.id] = new_user

        db.session.commit()
        print(f"Migrated {len(old_users)} users")

        # Migrate events to shows
        print("Migrating events to shows...")
        show_mapping = {}
        for old_event in old_events:
            new_show = Show(
                id=old_event.id,
                name=old_event.name,
                venue=old_event.venue,
                address=old_event.address,
                description=old_event.description,
                day_of_week=old_event.day_of_week,
                start_time=old_event.start_time,
                end_time=old_event.end_time,
                max_signups=old_event.max_signups,
                signup_window_before_days=14,  # Default value
                signup_window_after_hours=old_event.signup_deadline_hours,
                owner_id=old_event.host_id,
                default_host_id=old_event.host_id,
                started_date=(
                    old_event.created_at.date()
                    if old_event.created_at
                    else date.today()
                ),
                is_deleted=not old_event.is_active,
                created_at=old_event.created_at,
            )
            db.session.add(new_show)
            show_mapping[old_event.id] = new_show

        db.session.commit()
        print(f"Migrated {len(old_events)} events to shows")

        # Create show instances based on signups and cancellations
        print("Creating show instances...")
        instance_mapping = {}

        # Collect all dates that had activity (signups or cancellations)
        dates_with_activity = set()

        for signup in old_signups:
            dates_with_activity.add((signup.event_id, signup.event_date))

        for cancellation in old_cancellations:
            dates_with_activity.add(
                (cancellation.event_id, cancellation.cancelled_date)
            )

        # Also add recent future dates for active shows
        today = date.today()
        for old_event in old_events:
            if old_event.is_active:
                # Add next 8 weeks of instances
                for weeks_ahead in range(8):
                    check_date = today + timedelta(weeks=weeks_ahead)
                    days_ahead = 0
                    while days_ahead < 7:
                        instance_date = check_date + timedelta(days=days_ahead)
                        if instance_date.strftime("%A") == old_event.day_of_week:
                            dates_with_activity.add((old_event.id, instance_date))
                            break
                        days_ahead += 1

        # Create show instances
        for event_id, instance_date in dates_with_activity:
            if event_id in show_mapping:
                show = show_mapping[event_id]

                # Check if this date was cancelled
                cancellation = next(
                    (
                        c
                        for c in old_cancellations
                        if c.event_id == event_id and c.cancelled_date == instance_date
                    ),
                    None,
                )

                instance = ShowInstance(
                    show_id=show.id,
                    instance_date=instance_date,
                    is_cancelled=bool(cancellation),
                    cancellation_reason=cancellation.reason if cancellation else None,
                    cancelled_at=cancellation.created_at if cancellation else None,
                )
                db.session.add(instance)
                instance_mapping[(event_id, instance_date)] = instance

        db.session.commit()
        print(f"Created {len(instance_mapping)} show instances")

        # Migrate signups
        print("Migrating signups...")
        for old_signup in old_signups:
            instance_key = (old_signup.event_id, old_signup.event_date)
            if instance_key in instance_mapping:
                instance = instance_mapping[instance_key]

                new_signup = Signup(
                    comedian_id=old_signup.comedian_id,
                    show_instance_id=instance.id,
                    signup_time=old_signup.signup_time,
                    position=old_signup.position,
                    performed=old_signup.performed,
                    notes=old_signup.notes,
                )
                db.session.add(new_signup)

        db.session.commit()
        print(f"Migrated {len(old_signups)} signups")

        print("Migration completed successfully!")

        # Print summary
        show_count = Show.query.count()
        instance_count = ShowInstance.query.count()
        signup_count = Signup.query.count()
        user_count = User.query.count()

        print(f"\nMigration Summary:")
        print(f"Users: {user_count}")
        print(f"Shows: {show_count}")
        print(f"Show Instances: {instance_count}")
        print(f"Signups: {signup_count}")


if __name__ == "__main__":
    migrate_data()
