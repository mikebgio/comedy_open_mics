#!/usr/bin/env python3
"""
Seed script to populate the database with dummy data for testing
"""
import random
from datetime import datetime, time, timedelta

from app import app, db
from models import Show, ShowInstance, Signup, User

# Realistic comedian names and Boston venues
COMEDIAN_NAMES = [
    ("Alex", "Mitchell"),
    ("Sarah", "Chen"),
    ("Mike", "O'Connor"),
    ("Emma", "Rodriguez"),
    ("Jake", "Thompson"),
    ("Maya", "Patel"),
    ("Chris", "Johnson"),
    ("Zoe", "Williams"),
    ("Ryan", "Davis"),
    ("Lily", "Brown"),
    ("Sam", "Garcia"),
    ("Nina", "Wilson"),
    ("Tyler", "Jones"),
    ("Ava", "Taylor"),
    ("Jordan", "Anderson"),
    ("Sophia", "Martinez"),
    ("Dylan", "Moore"),
    ("Chloe", "Jackson"),
    ("Austin", "White"),
    ("Grace", "Harris"),
    ("Noah", "Clark"),
    ("Mia", "Lewis"),
    ("Logan", "Walker"),
    ("Ella", "Hall"),
    ("Luke", "Young"),
    ("Madison", "Allen"),
    ("Owen", "King"),
    ("Aria", "Wright"),
    ("Mason", "Lopez"),
    ("Layla", "Hill"),
    ("Carter", "Scott"),
    ("Zara", "Green"),
    ("Ethan", "Adams"),
    ("Ruby", "Baker"),
    ("Caleb", "Gonzalez"),
    ("Luna", "Nelson"),
]

BOSTON_VENUES = [
    {
        "name": "The Comedy Studio",
        "venue": "The Comedy Studio",
        "address": "1238 Massachusetts Ave, Cambridge, MA",
        "day": "Monday",
        "start_time": time(19, 30),
        "end_time": time(22, 0),
        "description": "Cambridge's premier comedy club featuring up-and-coming comedians.",
    },
    {
        "name": "Nick's Comedy Stop",
        "venue": "Nick's Comedy Stop",
        "address": "100 Warrenton St, Boston, MA",
        "day": "Tuesday",
        "start_time": time(20, 0),
        "end_time": None,
        "description": "Boston's longest running comedy club in the Theater District.",
    },
    {
        "name": "Laugh Boston",
        "venue": "Laugh Boston",
        "address": "425 Summer St, Boston, MA",
        "day": "Wednesday",
        "start_time": time(19, 0),
        "end_time": time(21, 30),
        "description": "State-of-the-art comedy venue in the Seaport District.",
    },
    {
        "name": "ImprovBoston",
        "venue": "ImprovBoston",
        "address": "40 Prospect St, Cambridge, MA",
        "day": "Thursday",
        "start_time": time(20, 30),
        "end_time": None,
        "description": "Improv and stand-up comedy in the heart of Cambridge.",
    },
    {
        "name": "The Hideout",
        "venue": "The Hideout",
        "address": "3 Harriet St, Cambridge, MA",
        "day": "Monday",
        "start_time": time(21, 0),
        "end_time": time(23, 0),
        "description": "Intimate venue in Central Square featuring experimental comedy.",
    },
    {
        "name": "Good Life Bar",
        "venue": "Good Life Bar",
        "address": "28 Kingston St, Boston, MA",
        "day": "Tuesday",
        "start_time": time(19, 30),
        "end_time": None,
        "description": "Downtown Boston bar with weekly comedy nights.",
    },
    {
        "name": "Tavern in the Square",
        "venue": "Tavern in the Square",
        "address": "1815 Massachusetts Ave, Cambridge, MA",
        "day": "Wednesday",
        "start_time": time(20, 0),
        "end_time": time(22, 30),
        "description": "Porter Square restaurant and bar hosting open mic nights.",
    },
    {
        "name": "The Sinclair",
        "venue": "The Sinclair",
        "address": "52 Church St, Cambridge, MA",
        "day": "Thursday",
        "start_time": time(18, 30),
        "end_time": time(21, 0),
        "description": "Music venue in Harvard Square with comedy showcases.",
    },
]


def create_users():
    """Create 36 realistic users"""
    users = []

    for i, (first_name, last_name) in enumerate(COMEDIAN_NAMES):
        # Create email from name
        email = f"{first_name.lower()}.{last_name.lower()}@email.com"
        username = f"{first_name.lower()}{last_name.lower()}"

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            email_verified=True,
        )
        user.set_password("password123")  # Simple password for testing
        users.append(user)

    return users


def create_events(users):
    """Create shows for some users (max 8)"""
    # Select 8 random users to be hosts
    host_users = random.sample(users, 8)
    shows = []

    # Signup timing variations for realistic data
    signup_timing_options = [
        (2880, 0),      # 2 days before, closes at show start
        (4320, 30),     # 3 days before, closes 30 minutes before show
        (1440, -15),    # 1 day before, closes 15 minutes into show
        (10080, 60),    # 1 week before, closes 1 hour before show
        (720, 0),       # 12 hours before, closes at show start
        (2160, 120),    # 1.5 days before, closes 2 hours before show
        (7200, 0),      # 5 days before, closes at show start
        (1080, -30),    # 18 hours before, closes 30 minutes into show
    ]

    for i, venue_data in enumerate(BOSTON_VENUES):
        if i >= len(host_users):
            break

        host = host_users[i]
        
        # Get signup timing for this show
        signups_open, signups_closed = signup_timing_options[i % len(signup_timing_options)]

        show = Show(
            name=venue_data["name"],
            venue=venue_data["venue"],
            address=venue_data["address"],
            day_of_week=venue_data["day"],
            start_time=venue_data["start_time"],
            end_time=venue_data["end_time"],
            description=venue_data["description"],
            max_signups=random.randint(15, 25),
            signups_open=signups_open,
            signups_closed=signups_closed,
            signup_window_after_hours=random.randint(1, 4),  # Keep for backward compatibility
            owner_id=host.id,
            default_host_id=host.id,
            timezone="America/New_York",
            repeat_cadence="weekly",
        )
        shows.append(show)

    return shows


def create_signups(users, shows):
    """Create some random signups for shows"""
    signups = []

    # Create show instances first
    for show in shows:
        # Create a few upcoming instances for each show
        for weeks_ahead in range(1, 4):  # Next 3 weeks
            instance_date = datetime.now().date() + timedelta(weeks=weeks_ahead)
            
            # Adjust to the correct day of the week
            days_ahead = (
                list(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).index(show.day_of_week) 
                - instance_date.weekday()
            ) % 7
            if days_ahead == 0 and weeks_ahead == 1:
                days_ahead = 7  # Next week, not this week
            
            instance_date = instance_date + timedelta(days=days_ahead)
            
            instance = ShowInstance(
                show_id=show.id,
                instance_date=instance_date
            )
            db.session.add(instance)
            
        db.session.flush()  # Get the instance IDs

    # Now create signups for instances
    instances = ShowInstance.query.all()
    for instance in instances:
        # Random number of signups for each instance (30-80% of max capacity)
        num_signups = random.randint(
            int(instance.show.max_signups * 0.3), int(instance.show.max_signups * 0.8)
        )

        # Select random users for signups (excluding the show owner)
        available_users = [u for u in users if u.id != instance.show.owner_id]
        signup_users = random.sample(available_users, min(num_signups, len(available_users)))

        for i, user in enumerate(signup_users):
            signup = Signup(
                comedian_id=user.id,
                show_instance_id=instance.id,
                signup_time=datetime.now()
                - timedelta(days=random.randint(1, 10)),  # Random signup time
                position=i + 1,  # Position in lineup
            )
            signups.append(signup)

    return signups


def seed_database():
    """Main function to seed the database"""
    with app.app_context():
        print("Creating users...")
        users = create_users()

        # Add users to session first so they get IDs
        for user in users:
            db.session.add(user)
        db.session.commit()
        print(f"Created {len(users)} users")

        print("Creating shows...")
        shows = create_events(users)

        # Add shows to session
        for show in shows:
            db.session.add(show)
        db.session.commit()
        print(f"Created {len(shows)} shows")

        print("Creating signups...")
        signups = create_signups(users, shows)

        # Add signups to session
        for signup in signups:
            db.session.add(signup)
        db.session.commit()
        print(f"Created {len(signups)} signups")

        print("Database seeded successfully!")
        print(f"Total users: {User.query.count()}")
        print(f"Total shows: {Show.query.count()}")
        print(f"Total show instances: {ShowInstance.query.count()}")
        print(f"Total signups: {Signup.query.count()}")


if __name__ == "__main__":
    # Clear existing data (optional - comment out to keep existing data)
    with app.app_context():
        print("Clearing existing data...")
        Signup.query.delete()
        ShowInstance.query.delete()
        Show.query.delete()
        User.query.delete()
        db.session.commit()

    seed_database()
