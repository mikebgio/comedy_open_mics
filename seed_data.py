#!/usr/bin/env python3
"""
Seed script to populate the database with dummy data for testing
"""
import random
from datetime import time, datetime, timedelta
from app import app, db
from models import User, Event, Signup
from werkzeug.security import generate_password_hash

# Realistic comedian names and Boston venues
COMEDIAN_NAMES = [
    ("Alex", "Mitchell"), ("Sarah", "Chen"), ("Mike", "O'Connor"), ("Emma", "Rodriguez"),
    ("Jake", "Thompson"), ("Maya", "Patel"), ("Chris", "Johnson"), ("Zoe", "Williams"),
    ("Ryan", "Davis"), ("Lily", "Brown"), ("Sam", "Garcia"), ("Nina", "Wilson"),
    ("Tyler", "Jones"), ("Ava", "Taylor"), ("Jordan", "Anderson"), ("Sophia", "Martinez"),
    ("Dylan", "Moore"), ("Chloe", "Jackson"), ("Austin", "White"), ("Grace", "Harris"),
    ("Noah", "Clark"), ("Mia", "Lewis"), ("Logan", "Walker"), ("Ella", "Hall"),
    ("Luke", "Young"), ("Madison", "Allen"), ("Owen", "King"), ("Aria", "Wright"),
    ("Mason", "Lopez"), ("Layla", "Hill"), ("Carter", "Scott"), ("Zara", "Green"),
    ("Ethan", "Adams"), ("Ruby", "Baker"), ("Caleb", "Gonzalez"), ("Luna", "Nelson")
]

BOSTON_VENUES = [
    {
        "name": "The Comedy Studio",
        "venue": "The Comedy Studio",
        "address": "1238 Massachusetts Ave, Cambridge, MA",
        "day": "Monday",
        "start_time": time(19, 30),
        "end_time": time(22, 0),
        "description": "Cambridge's premier comedy club featuring up-and-coming comedians."
    },
    {
        "name": "Nick's Comedy Stop",
        "venue": "Nick's Comedy Stop", 
        "address": "100 Warrenton St, Boston, MA",
        "day": "Tuesday",
        "start_time": time(20, 0),
        "end_time": None,
        "description": "Boston's longest running comedy club in the Theater District."
    },
    {
        "name": "Laugh Boston",
        "venue": "Laugh Boston",
        "address": "425 Summer St, Boston, MA",
        "day": "Wednesday", 
        "start_time": time(19, 0),
        "end_time": time(21, 30),
        "description": "State-of-the-art comedy venue in the Seaport District."
    },
    {
        "name": "ImprovBoston",
        "venue": "ImprovBoston",
        "address": "40 Prospect St, Cambridge, MA",
        "day": "Thursday",
        "start_time": time(20, 30),
        "end_time": None,
        "description": "Improv and stand-up comedy in the heart of Cambridge."
    },
    {
        "name": "The Hideout",
        "venue": "The Hideout",
        "address": "3 Harriet St, Cambridge, MA", 
        "day": "Monday",
        "start_time": time(21, 0),
        "end_time": time(23, 0),
        "description": "Intimate venue in Central Square featuring experimental comedy."
    },
    {
        "name": "Good Life Bar",
        "venue": "Good Life Bar",
        "address": "28 Kingston St, Boston, MA",
        "day": "Tuesday",
        "start_time": time(19, 30),
        "end_time": None,
        "description": "Downtown Boston bar with weekly comedy nights."
    },
    {
        "name": "Tavern in the Square",
        "venue": "Tavern in the Square",
        "address": "1815 Massachusetts Ave, Cambridge, MA",
        "day": "Wednesday",
        "start_time": time(20, 0),
        "end_time": time(22, 30),
        "description": "Porter Square restaurant and bar hosting open mic nights."
    },
    {
        "name": "The Sinclair",
        "venue": "The Sinclair",
        "address": "52 Church St, Cambridge, MA",
        "day": "Thursday", 
        "start_time": time(18, 30),
        "end_time": time(21, 0),
        "description": "Music venue in Harvard Square with comedy showcases."
    }
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
            is_comedian=True,
            is_host=False,
            email_verified=True
        )
        user.set_password("password123")  # Simple password for testing
        users.append(user)
        
    return users

def create_events(users):
    """Create events for some users (max 8)"""
    # Select 8 random users to be hosts
    host_users = random.sample(users, 8)
    events = []
    
    for i, venue_data in enumerate(BOSTON_VENUES):
        if i >= len(host_users):
            break
            
        host = host_users[i]
        host.is_host = True  # Make them a host
        
        event = Event(
            name=venue_data["name"],
            venue=venue_data["venue"],
            address=venue_data["address"],
            day_of_week=venue_data["day"],
            start_time=venue_data["start_time"],
            end_time=venue_data["end_time"],
            description=venue_data["description"],
            max_signups=random.randint(15, 25),
            signup_deadline_hours=random.randint(1, 4),
            host_id=host.id,
            is_active=True
        )
        events.append(event)
    
    return events

def create_signups(users, events):
    """Create some random signups for events"""
    signups = []
    
    # Get current date and next few weeks
    today = datetime.now().date()
    
    for event in events:
        # Find next occurrence of this day of week
        days_ahead = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        
        target_weekday = days_ahead[event.day_of_week]
        days_until_target = (target_weekday - today.weekday()) % 7
        if days_until_target == 0:  # If it's today, move to next week
            days_until_target = 7
            
        event_date = today + timedelta(days=days_until_target)
        
        # Create signups for 3-8 random comedians for each event
        num_signups = random.randint(3, min(8, event.max_signups))
        selected_comedians = random.sample([u for u in users if not u.is_host], num_signups)
        
        for position, comedian in enumerate(selected_comedians, 1):
            signup = Signup(
                comedian_id=comedian.id,
                event_id=event.id,
                event_date=event_date,
                position=position,
                performed=False,
                notes=random.choice([
                    None, 
                    "Working on new material", 
                    "First time here!", 
                    "Trying out crowd work",
                    "New 5-minute set"
                ])
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
        
        print("Creating events...")
        events = create_events(users)
        
        # Add events to session
        for event in events:
            db.session.add(event)
        db.session.commit()
        print(f"Created {len(events)} events")
        
        print("Creating signups...")
        signups = create_signups(users, events)
        
        # Add signups to session
        for signup in signups:
            db.session.add(signup)
        db.session.commit()
        print(f"Created {len(signups)} signups")
        
        print("Database seeded successfully!")
        print(f"Total users: {User.query.count()}")
        print(f"Total events: {Event.query.count()}")
        print(f"Total signups: {Signup.query.count()}")

if __name__ == "__main__":
    # Clear existing data (optional - comment out to keep existing data)
    with app.app_context():
        print("Clearing existing data...")
        Signup.query.delete()
        Event.query.delete()
        User.query.delete()
        db.session.commit()
    
    seed_database()