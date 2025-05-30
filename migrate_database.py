#!/usr/bin/env python3
"""
Safe migration script to transform existing data to new Show/ShowInstance model
"""
import os
import sys
from datetime import date, datetime, timedelta

# Set up the application context
sys.path.insert(0, os.path.dirname(__file__))


def migrate_database():
    """Perform the database migration safely"""

    # Import with backup models first
    from app import app, db
    from models_backup import Event as OldEvent
    from models_backup import EventCancellation as OldEventCancellation
    from models_backup import Signup as OldSignup
    from models_backup import User as OldUser

    with app.app_context():
        print("Starting safe database migration...")

        # Collect all existing data
        print("Backing up existing data...")
        users_data = []
        events_data = []
        signups_data = []
        cancellations_data = []

        try:
            for user in OldUser.query.all():
                users_data.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "password_hash": user.password_hash,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email_verified": user.email_verified,
                        "email_verification_token": user.email_verification_token,
                        "created_at": user.created_at,
                        "is_comedian": getattr(user, "is_comedian", True),
                        "is_host": getattr(user, "is_host", False),
                    }
                )

            for event in OldEvent.query.all():
                events_data.append(
                    {
                        "id": event.id,
                        "name": event.name,
                        "venue": event.venue,
                        "address": event.address,
                        "description": getattr(event, "description", ""),
                        "day_of_week": event.day_of_week,
                        "start_time": event.start_time,
                        "end_time": event.end_time,
                        "max_signups": event.max_signups,
                        "signup_deadline_hours": event.signup_deadline_hours,
                        "host_id": event.host_id,
                        "is_active": event.is_active,
                        "created_at": event.created_at,
                    }
                )

            for signup in OldSignup.query.all():
                signups_data.append(
                    {
                        "id": signup.id,
                        "comedian_id": signup.comedian_id,
                        "event_id": signup.event_id,
                        "event_date": signup.event_date,
                        "signup_time": signup.signup_time,
                        "position": signup.position,
                        "performed": signup.performed,
                        "notes": signup.notes,
                    }
                )

            for cancellation in OldEventCancellation.query.all():
                cancellations_data.append(
                    {
                        "id": cancellation.id,
                        "event_id": cancellation.event_id,
                        "cancelled_date": cancellation.cancelled_date,
                        "reason": cancellation.reason,
                        "created_at": cancellation.created_at,
                    }
                )

        except Exception as e:
            print(f"Error backing up data: {e}")
            return False

        print(
            f"Backed up {len(users_data)} users, {len(events_data)} events, {len(signups_data)} signups, {len(cancellations_data)} cancellations"
        )

        # Drop all tables
        print("Dropping existing tables...")
        try:
            db.drop_all()
        except Exception as e:
            print(f"Error dropping tables: {e}")

        # Import new models and create tables
        print("Creating new database schema...")
        from models import (
            Show,
            ShowHost,
            ShowInstance,
            ShowInstanceHost,
            ShowRunner,
            Signup,
            User,
        )

        try:
            db.create_all()
        except Exception as e:
            print(f"Error creating new tables: {e}")
            return False

        # Migrate users
        print("Migrating users...")
        for user_data in users_data:
            try:
                user = User(
                    id=user_data["id"],
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    email_verified=user_data["email_verified"],
                    email_verification_token=user_data["email_verification_token"],
                    created_at=user_data["created_at"],
                )
                db.session.add(user)
            except Exception as e:
                print(f"Error migrating user {user_data['username']}: {e}")

        try:
            db.session.commit()
            print(f"Migrated {len(users_data)} users")
        except Exception as e:
            print(f"Error committing users: {e}")
            db.session.rollback()
            return False

        # Migrate events to shows
        print("Migrating events to shows...")
        show_mapping = {}

        for event_data in events_data:
            try:
                show = Show(
                    id=event_data["id"],
                    name=event_data["name"],
                    venue=event_data["venue"],
                    address=event_data["address"],
                    description=event_data["description"],
                    day_of_week=event_data["day_of_week"],
                    start_time=event_data["start_time"],
                    end_time=event_data["end_time"],
                    max_signups=event_data["max_signups"],
                    signup_window_before_days=14,
                    signup_window_after_hours=event_data["signup_deadline_hours"],
                    owner_id=event_data["host_id"],
                    default_host_id=event_data["host_id"],
                    started_date=(
                        event_data["created_at"].date()
                        if event_data["created_at"]
                        else date.today()
                    ),
                    is_deleted=not event_data["is_active"],
                    created_at=event_data["created_at"],
                    updated_at=event_data["created_at"],
                )
                db.session.add(show)
                show_mapping[event_data["id"]] = show
            except Exception as e:
                print(f"Error migrating event {event_data['name']}: {e}")

        try:
            db.session.commit()
            print(f"Migrated {len(events_data)} shows")
        except Exception as e:
            print(f"Error committing shows: {e}")
            db.session.rollback()
            return False

        # Create show instances
        print("Creating show instances...")
        instance_mapping = {}
        dates_with_activity = set()

        # Collect all dates that had signups or cancellations
        for signup_data in signups_data:
            dates_with_activity.add(
                (signup_data["event_id"], signup_data["event_date"])
            )

        for cancellation_data in cancellations_data:
            dates_with_activity.add(
                (cancellation_data["event_id"], cancellation_data["cancelled_date"])
            )

        # Add future instances for active shows
        today = date.today()
        for event_data in events_data:
            if event_data["is_active"]:
                for weeks_ahead in range(8):
                    current_week = today + timedelta(weeks=weeks_ahead)
                    for day_offset in range(7):
                        check_date = current_week + timedelta(days=day_offset)
                        if (
                            check_date.strftime("%A") == event_data["day_of_week"]
                            and check_date >= today
                        ):
                            dates_with_activity.add((event_data["id"], check_date))
                            break

        for event_id, instance_date in dates_with_activity:
            if event_id in show_mapping:
                # Check if cancelled
                cancellation = next(
                    (
                        c
                        for c in cancellations_data
                        if c["event_id"] == event_id
                        and c["cancelled_date"] == instance_date
                    ),
                    None,
                )

                try:
                    instance = ShowInstance(
                        show_id=event_id,
                        instance_date=instance_date,
                        is_cancelled=bool(cancellation),
                        cancellation_reason=(
                            cancellation["reason"] if cancellation else None
                        ),
                        cancelled_at=(
                            cancellation["created_at"] if cancellation else None
                        ),
                    )
                    db.session.add(instance)
                    instance_mapping[(event_id, instance_date)] = instance
                except Exception as e:
                    print(
                        f"Error creating instance for show {event_id} on {instance_date}: {e}"
                    )

        try:
            db.session.commit()
            print(f"Created {len(instance_mapping)} show instances")
        except Exception as e:
            print(f"Error committing instances: {e}")
            db.session.rollback()
            return False

        # Migrate signups
        print("Migrating signups...")
        migrated_signups = 0

        for signup_data in signups_data:
            instance_key = (signup_data["event_id"], signup_data["event_date"])
            if instance_key in instance_mapping:
                instance = instance_mapping[instance_key]
                try:
                    new_signup = Signup(
                        comedian_id=signup_data["comedian_id"],
                        show_instance_id=instance.id,
                        signup_time=signup_data["signup_time"],
                        position=signup_data["position"],
                        performed=signup_data["performed"],
                        notes=signup_data["notes"],
                    )
                    db.session.add(new_signup)
                    migrated_signups += 1
                except Exception as e:
                    print(f"Error migrating signup {signup_data['id']}: {e}")

        try:
            db.session.commit()
            print(f"Migrated {migrated_signups} signups")
        except Exception as e:
            print(f"Error committing signups: {e}")
            db.session.rollback()
            return False

        # Final verification
        final_users = User.query.count()
        final_shows = Show.query.count()
        final_instances = ShowInstance.query.count()
        final_signups = Signup.query.count()

        print("\nMigration completed successfully!")
        print(f"Final counts:")
        print(f"  Users: {final_users}")
        print(f"  Shows: {final_shows}")
        print(f"  Show Instances: {final_instances}")
        print(f"  Signups: {final_signups}")

        return True


if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("Migration completed successfully!")
        sys.exit(0)
    else:
        print("Migration failed!")
        sys.exit(1)
