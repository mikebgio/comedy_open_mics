#!/usr/bin/env python3
"""
Direct database migration using raw SQL and SQLAlchemy core
"""
import os
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text, MetaData

def migrate_database():
    """Perform direct database migration"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        return False
    
    engine = create_engine(database_url)
    
    print("Starting direct database migration...")
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # 1. Backup existing data
            print("Backing up existing data...")
            
            # Get users
            users_result = conn.execute(text("SELECT * FROM \"user\""))
            users_data = [dict(row._mapping) for row in users_result]
            
            # Get events  
            events_result = conn.execute(text("SELECT * FROM event"))
            events_data = [dict(row._mapping) for row in events_result]
            
            # Get signups
            signups_result = conn.execute(text("SELECT * FROM signup"))
            signups_data = [dict(row._mapping) for row in signups_result]
            
            # Get cancellations
            cancellations_result = conn.execute(text("SELECT * FROM event_cancellation"))
            cancellations_data = [dict(row._mapping) for row in cancellations_result]
            
            print(f"Backed up {len(users_data)} users, {len(events_data)} events, {len(signups_data)} signups, {len(cancellations_data)} cancellations")
            
            # 2. Drop old tables
            print("Dropping old tables...")
            conn.execute(text("DROP TABLE IF EXISTS signup CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS event_cancellation CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS event CASCADE"))
            # Don't drop user table, just modify it if needed
            
            # 3. Create new tables
            print("Creating new tables...")
            
            # Create show table
            conn.execute(text("""
                CREATE TABLE show (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    venue VARCHAR(100) NOT NULL,
                    address VARCHAR(200) NOT NULL,
                    description TEXT,
                    day_of_week VARCHAR(20) NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME,
                    repeat_cadence VARCHAR(20) DEFAULT 'weekly',
                    custom_repeat_days INTEGER,
                    started_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    ended_date DATE,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    max_signups INTEGER DEFAULT 20,
                    signup_window_before_days INTEGER DEFAULT 14,
                    signup_window_after_hours INTEGER DEFAULT 2,
                    owner_id INTEGER NOT NULL REFERENCES "user"(id),
                    default_host_id INTEGER REFERENCES "user"(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create show_runner table
            conn.execute(text("""
                CREATE TABLE show_runner (
                    id SERIAL PRIMARY KEY,
                    show_id INTEGER NOT NULL REFERENCES show(id),
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    added_by_id INTEGER NOT NULL REFERENCES "user"(id),
                    UNIQUE(show_id, user_id)
                )
            """))
            
            # Create show_host table
            conn.execute(text("""
                CREATE TABLE show_host (
                    id SERIAL PRIMARY KEY,
                    show_id INTEGER NOT NULL REFERENCES show(id),
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    added_by_id INTEGER NOT NULL REFERENCES "user"(id),
                    UNIQUE(show_id, user_id)
                )
            """))
            
            # Create show_instance table
            conn.execute(text("""
                CREATE TABLE show_instance (
                    id SERIAL PRIMARY KEY,
                    show_id INTEGER NOT NULL REFERENCES show(id),
                    instance_date DATE NOT NULL,
                    is_cancelled BOOLEAN DEFAULT FALSE,
                    cancellation_reason VARCHAR(200),
                    cancelled_at TIMESTAMP,
                    max_signups_override INTEGER,
                    start_time_override TIME,
                    end_time_override TIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(show_id, instance_date)
                )
            """))
            
            # Create show_instance_host table
            conn.execute(text("""
                CREATE TABLE show_instance_host (
                    id SERIAL PRIMARY KEY,
                    show_instance_id INTEGER NOT NULL REFERENCES show_instance(id),
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(show_instance_id, user_id)
                )
            """))
            
            # Create new signup table
            conn.execute(text("""
                CREATE TABLE signup (
                    id SERIAL PRIMARY KEY,
                    comedian_id INTEGER NOT NULL REFERENCES "user"(id),
                    show_instance_id INTEGER NOT NULL REFERENCES show_instance(id),
                    signup_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    position INTEGER,
                    is_present BOOLEAN,
                    performed BOOLEAN DEFAULT FALSE,
                    notes TEXT,
                    UNIQUE(comedian_id, show_instance_id)
                )
            """))
            
            # 4. Migrate data
            print("Migrating events to shows...")
            
            # Insert shows from events
            for event in events_data:
                conn.execute(text("""
                    INSERT INTO show (
                        id, name, venue, address, description, day_of_week, 
                        start_time, end_time, max_signups, signup_window_after_hours,
                        owner_id, default_host_id, started_date, is_deleted, created_at, updated_at
                    ) VALUES (
                        :id, :name, :venue, :address, :description, :day_of_week,
                        :start_time, :end_time, :max_signups, :signup_deadline_hours,
                        :host_id, :host_id, :created_at, :is_deleted, :created_at, :created_at
                    )
                """), {
                    'id': event['id'],
                    'name': event['name'],
                    'venue': event['venue'],
                    'address': event['address'],
                    'description': event.get('description', ''),
                    'day_of_week': event['day_of_week'],
                    'start_time': event['start_time'],
                    'end_time': event['end_time'],
                    'max_signups': event['max_signups'],
                    'signup_deadline_hours': event['signup_deadline_hours'],
                    'host_id': event['host_id'],
                    'is_deleted': not event['is_active'],
                    'created_at': event['created_at']
                })
            
            print("Creating show instances...")
            
            # Collect all dates with activity
            dates_with_activity = set()
            
            for signup in signups_data:
                dates_with_activity.add((signup['event_id'], signup['event_date']))
            
            for cancellation in cancellations_data:
                dates_with_activity.add((cancellation['event_id'], cancellation['cancelled_date']))
            
            # Add future instances for active shows
            today = date.today()
            for event in events_data:
                if event['is_active']:
                    for weeks_ahead in range(8):
                        current_week = today + timedelta(weeks=weeks_ahead)
                        for day_offset in range(7):
                            check_date = current_week + timedelta(days=day_offset)
                            if check_date.strftime('%A') == event['day_of_week'] and check_date >= today:
                                dates_with_activity.add((event['id'], check_date))
                                break
            
            # Create show instances
            instance_id_counter = 1
            instance_mapping = {}
            
            for event_id, instance_date in dates_with_activity:
                # Check if this date was cancelled
                cancellation = next((c for c in cancellations_data 
                                   if c['event_id'] == event_id and c['cancelled_date'] == instance_date), None)
                
                conn.execute(text("""
                    INSERT INTO show_instance (
                        id, show_id, instance_date, is_cancelled, cancellation_reason, cancelled_at
                    ) VALUES (
                        :id, :show_id, :instance_date, :is_cancelled, :cancellation_reason, :cancelled_at
                    )
                """), {
                    'id': instance_id_counter,
                    'show_id': event_id,
                    'instance_date': instance_date,
                    'is_cancelled': bool(cancellation),
                    'cancellation_reason': cancellation['reason'] if cancellation else None,
                    'cancelled_at': cancellation['created_at'] if cancellation else None
                })
                
                instance_mapping[(event_id, instance_date)] = instance_id_counter
                instance_id_counter += 1
            
            print("Migrating signups...")
            
            # Migrate signups
            for signup in signups_data:
                instance_key = (signup['event_id'], signup['event_date'])
                if instance_key in instance_mapping:
                    instance_id = instance_mapping[instance_key]
                    
                    conn.execute(text("""
                        INSERT INTO signup (
                            comedian_id, show_instance_id, signup_time, position, performed, notes
                        ) VALUES (
                            :comedian_id, :show_instance_id, :signup_time, :position, :performed, :notes
                        )
                    """), {
                        'comedian_id': signup['comedian_id'],
                        'show_instance_id': instance_id,
                        'signup_time': signup['signup_time'],
                        'position': signup['position'],
                        'performed': signup['performed'],
                        'notes': signup['notes']
                    })
            
            # Update sequences
            conn.execute(text("SELECT setval('show_id_seq', (SELECT MAX(id) FROM show))"))
            conn.execute(text("SELECT setval('show_instance_id_seq', (SELECT MAX(id) FROM show_instance))"))
            conn.execute(text("SELECT setval('signup_id_seq', (SELECT MAX(id) FROM signup))"))
            
            # Commit transaction
            trans.commit()
            
            # Verify results
            show_count = conn.execute(text("SELECT COUNT(*) FROM show")).scalar()
            instance_count = conn.execute(text("SELECT COUNT(*) FROM show_instance")).scalar()
            signup_count = conn.execute(text("SELECT COUNT(*) FROM signup")).scalar()
            user_count = conn.execute(text("SELECT COUNT(*) FROM \"user\"")).scalar()
            
            print("\nMigration completed successfully!")
            print(f"Final counts:")
            print(f"  Users: {user_count}")
            print(f"  Shows: {show_count}")
            print(f"  Show Instances: {instance_count}")
            print(f"  Signups: {signup_count}")
            
            return True
            
        except Exception as e:
            print(f"Error during migration: {e}")
            trans.rollback()
            return False

if __name__ == '__main__':
    success = migrate_database()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")