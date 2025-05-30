import random
import calendar
from datetime import datetime, date, timedelta
from urllib.parse import urlparse, urljoin
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Event, Signup, EventCancellation
from forms import RegistrationForm, LoginForm, EventForm, SignupForm, CancellationForm


def is_safe_url(target):
    """Check if the target URL is safe for redirects (same domain only)."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@app.route('/')
def index():
    # Get upcoming events
    today = date.today()
    upcoming_events = Event.query.filter_by(is_active=True).all()
    
    # Filter out cancelled events for today
    events_today = []
    for event in upcoming_events:
        # Check if today matches the event's day of week
        if today.strftime('%A') == event.day_of_week:
            # Check if not cancelled
            cancellation = EventCancellation.query.filter_by(
                event_id=event.id, 
                cancelled_date=today
            ).first()
            if not cancellation:
                events_today.append(event)
    
    return render_template('index.html', events_today=events_today)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data.lower().strip(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            is_comedian=True,
            is_host=False
        )
        user.set_password(form.password.data)
        user.email_verified = True  # Skip email verification
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or not is_safe_url(next_page):
                return redirect(url_for('dashboard'))
            return redirect(next_page)
        flash('Invalid username or password')
    
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))





@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.email_verified:
        flash('Please verify your email address to access all features.')
        
    if current_user.is_host and current_user.is_comedian:
        # Show combined dashboard or let user choose
        return render_template('combined_dashboard.html')
    elif current_user.is_host:
        return redirect(url_for('host_dashboard'))
    else:
        return redirect(url_for('comedian_dashboard'))

@app.route('/comedian/dashboard')
@login_required
def comedian_dashboard():
    if not current_user.is_comedian:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Get comedian's upcoming signups
    today = date.today()
    upcoming_signups = Signup.query.filter(
        Signup.comedian_id == current_user.id,
        Signup.event_date >= today
    ).order_by(Signup.event_date).all()
    
    # Get available events for signup
    events = Event.query.filter_by(is_active=True).all()
    
    return render_template('comedian/dashboard.html', 
                         upcoming_signups=upcoming_signups, 
                         events=events)

@app.route('/comedian/signup/<int:event_id>', methods=['GET', 'POST'])
@login_required
def signup_for_event(event_id):
    if not current_user.is_comedian:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    form = SignupForm()
    
    # Calculate next event date
    today = date.today()
    days_ahead = (list(range(7))[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(event.day_of_week)] - today.weekday()) % 7
    if days_ahead == 0:  # Today
        next_event_date = today
    else:
        next_event_date = today + timedelta(days=days_ahead)
    
    # Check if already signed up
    existing_signup = Signup.query.filter_by(
        comedian_id=current_user.id,
        event_id=event_id,
        event_date=next_event_date
    ).first()
    
    if existing_signup:
        flash('You are already signed up for this event.')
        return redirect(url_for('comedian_dashboard'))
    
    # Check if event is cancelled
    cancellation = EventCancellation.query.filter_by(
        event_id=event_id,
        cancelled_date=next_event_date
    ).first()
    
    if cancellation:
        flash('This event is cancelled for the selected date.')
        return redirect(url_for('comedian_dashboard'))
    
    if form.validate_on_submit():
        # Check signup deadline
        event_datetime = datetime.combine(next_event_date, event.start_time)
        deadline = event_datetime - timedelta(hours=event.signup_deadline_hours)
        
        if datetime.now() > deadline:
            flash('Signup deadline has passed.')
            return redirect(url_for('comedian_dashboard'))
        
        # Check max signups
        current_signups = Signup.query.filter_by(
            event_id=event_id,
            event_date=next_event_date
        ).count()
        
        if current_signups >= event.max_signups:
            flash('This event is full.')
            return redirect(url_for('comedian_dashboard'))
        
        signup = Signup(
            comedian_id=current_user.id,
            event_id=event_id,
            event_date=next_event_date,
            notes=form.notes.data
        )
        db.session.add(signup)
        db.session.commit()
        flash('Successfully signed up for the event!')
        return redirect(url_for('comedian_dashboard'))
    
    return render_template('comedian/signup.html', form=form, event=event, next_date=next_event_date)

@app.route('/host/dashboard')
@login_required
def host_dashboard():
    if not current_user.is_host:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    events = Event.query.filter_by(host_id=current_user.id).all()
    return render_template('host/dashboard.html', events=events)

@app.route('/host/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    # Allow any user to create events, making them a host
    if not current_user.is_host:
        current_user.become_host()
        db.session.commit()
    
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            name=form.name.data,
            venue=form.venue.data,
            address=form.address.data,
            day_of_week=form.day_of_week.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            description=form.description.data,
            max_signups=form.max_signups.data,
            signup_deadline_hours=form.signup_deadline_hours.data,
            host_id=current_user.id
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!')
        return redirect(url_for('host_dashboard'))
    
    return render_template('host/create_event.html', form=form)

@app.route('/host/manage_lineup/<int:event_id>')
@login_required
def manage_lineup(event_id):
    if not current_user.is_host:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    if event.host_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('host_dashboard'))
    
    # Get today's date or next occurrence
    today = date.today()
    days_ahead = (list(range(7))[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(event.day_of_week)] - today.weekday()) % 7
    if days_ahead == 0:
        event_date = today
    else:
        event_date = today + timedelta(days=days_ahead)
    
    # Get signups for this date
    signups = Signup.query.filter_by(
        event_id=event_id,
        event_date=event_date
    ).order_by(Signup.position.asc().nullslast(), Signup.signup_time).all()
    
    return render_template('host/manage_lineup.html', event=event, signups=signups, event_date=event_date)

@app.route('/host/reorder_lineup/<int:event_id>', methods=['POST'])
@login_required
def reorder_lineup(event_id):
    if not current_user.is_host:
        return jsonify({'error': 'Access denied'}), 403
    
    event = Event.query.get_or_404(event_id)
    if event.host_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    signup_ids = request.json.get('signup_ids', [])
    
    for i, signup_id in enumerate(signup_ids):
        signup = Signup.query.get(signup_id)
        if signup and signup.event_id == event_id:
            signup.position = i + 1
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/host/random_select/<int:event_id>')
@login_required
def random_select(event_id):
    if not current_user.is_host:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    if event.host_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('host_dashboard'))
    
    # Get today's signups without positions
    today = date.today()
    days_ahead = (list(range(7))[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(event.day_of_week)] - today.weekday()) % 7
    if days_ahead == 0:
        event_date = today
    else:
        event_date = today + timedelta(days=days_ahead)
    
    unpositioned_signups = Signup.query.filter_by(
        event_id=event_id,
        event_date=event_date,
        position=None
    ).all()
    
    if unpositioned_signups:
        # Get the highest current position
        max_position = db.session.query(db.func.max(Signup.position)).filter_by(
            event_id=event_id,
            event_date=event_date
        ).scalar() or 0
        
        # Select random comedian
        selected_signup = random.choice(unpositioned_signups)
        selected_signup.position = max_position + 1
        db.session.commit()
        
        flash(f'Selected: {selected_signup.comedian.full_name}')
    else:
        flash('No unpositioned comedians available.')
    
    return redirect(url_for('manage_lineup', event_id=event_id))

@app.route('/host/cancel_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def cancel_event(event_id):
    if not current_user.is_host:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    if event.host_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('host_dashboard'))
    
    form = CancellationForm()
    if form.validate_on_submit():
        # Check if already cancelled
        existing = EventCancellation.query.filter_by(
            event_id=event_id,
            cancelled_date=form.cancelled_date.data
        ).first()
        
        if existing:
            flash('Event is already cancelled for this date.')
        else:
            cancellation = EventCancellation(
                event_id=event_id,
                cancelled_date=form.cancelled_date.data,
                reason=form.reason.data
            )
            db.session.add(cancellation)
            db.session.commit()
            flash('Event cancelled successfully.')
        
        return redirect(url_for('host_dashboard'))
    
    return render_template('host/cancel_event.html', form=form, event=event)

@app.route('/event/<int:event_id>')
def event_info(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Get recent cancellations
    recent_cancellations = EventCancellation.query.filter(
        EventCancellation.event_id == event_id,
        EventCancellation.cancelled_date >= date.today()
    ).order_by(EventCancellation.cancelled_date).all()
    
    return render_template('public/event_info.html', event=event, cancellations=recent_cancellations)

@app.route('/lineup/<int:event_id>')
def live_lineup(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Get today's lineup
    today = date.today()
    current_time = datetime.now()
    days_ahead = (list(range(7))[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(event.day_of_week)] - today.weekday()) % 7
    if days_ahead == 0:
        event_date = today
    else:
        event_date = today + timedelta(days=days_ahead)
    
    # Check if cancelled
    cancellation = EventCancellation.query.filter_by(
        event_id=event_id,
        cancelled_date=event_date
    ).first()
    
    if cancellation:
        return render_template('public/live_lineup.html', 
                             event=event, 
                             signups=[], 
                             event_date=event_date,
                             current_time=current_time,
                             is_cancelled=True,
                             cancellation_reason=cancellation.reason)
    
    signups = Signup.query.filter_by(
        event_id=event_id,
        event_date=event_date
    ).order_by(Signup.position.asc().nullslast(), Signup.signup_time).all()
    
    return render_template('public/live_lineup.html', 
                         event=event, 
                         signups=signups, 
                         event_date=event_date,
                         current_time=current_time,
                         is_cancelled=False)

@app.route('/calendar')
@login_required
def calendar_view():
    # Get the current month or requested month
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    
    # Create calendar data
    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    month_days = cal.monthdayscalendar(year, month)
    
    # Get all events for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    events = Event.query.filter_by(is_active=True).all()
    
    # Create a dictionary of events by date
    events_by_date = {}
    for day in range(1, (end_date - start_date).days + 2):
        current_date = start_date + timedelta(days=day-1)
        events_by_date[current_date] = []
        
        for event in events:
            if current_date.strftime('%A') == event.day_of_week:
                # Check if not cancelled
                cancellation = EventCancellation.query.filter_by(
                    event_id=event.id,
                    cancelled_date=current_date
                ).first()
                
                if not cancellation:
                    # Get signup count for this date
                    signup_count = Signup.query.filter_by(
                        event_id=event.id,
                        event_date=current_date
                    ).count()
                    
                    event_data = {
                        'event': event,
                        'signup_count': signup_count,
                        'date': current_date
                    }
                    events_by_date[current_date].append(event_data)
    
    # Navigation dates
    if month == 1:
        prev_month = {'year': year - 1, 'month': 12}
    else:
        prev_month = {'year': year, 'month': month - 1}
    
    if month == 12:
        next_month = {'year': year + 1, 'month': 1}
    else:
        next_month = {'year': year, 'month': month + 1}
    
    return render_template('calendar.html', 
                         month_days=month_days,
                         events_by_date=events_by_date,
                         current_month=datetime(year, month, 1),
                         prev_month=prev_month,
                         next_month=next_month,
                         today=date.today())

@app.route('/api/move_event', methods=['POST'])
@login_required
def move_event():
    if not current_user.is_host:
        return jsonify({'error': 'Only hosts can move events'}), 403
    
    data = request.get_json()
    event_id = data.get('event_id')
    old_date = datetime.strptime(data.get('old_date'), '%Y-%m-%d').date()
    new_date = datetime.strptime(data.get('new_date'), '%Y-%m-%d').date()
    
    event = Event.query.get_or_404(event_id)
    
    # Check if user owns this event
    if event.host_id != current_user.id:
        return jsonify({'error': 'You can only move your own events'}), 403
    
    # Update the event's day of week
    event.day_of_week = new_date.strftime('%A')
    
    # Move all signups from old date to new date
    signups = Signup.query.filter_by(event_id=event_id, event_date=old_date).all()
    for signup in signups:
        signup.event_date = new_date
    
    # Move any cancellations
    cancellations = EventCancellation.query.filter_by(event_id=event_id, cancelled_date=old_date).all()
    for cancellation in cancellations:
        cancellation.cancelled_date = new_date
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Event moved successfully'})

@app.route('/api/calendar_events')
@login_required
def calendar_events_api():
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    
    # Get events for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    events = Event.query.filter_by(is_active=True).all()
    
    calendar_events = []
    for day in range(1, (end_date - start_date).days + 2):
        current_date = start_date + timedelta(days=day-1)
        
        for event in events:
            if current_date.strftime('%A') == event.day_of_week:
                # Check if not cancelled
                cancellation = EventCancellation.query.filter_by(
                    event_id=event.id,
                    cancelled_date=current_date
                ).first()
                
                if not cancellation:
                    signup_count = Signup.query.filter_by(
                        event_id=event.id,
                        event_date=current_date
                    ).count()
                    
                    calendar_events.append({
                        'id': event.id,
                        'title': event.name,
                        'venue': event.venue,
                        'start_time': event.start_time.strftime('%H:%M'),
                        'date': current_date.isoformat(),
                        'signup_count': signup_count,
                        'max_signups': event.max_signups,
                        'is_owner': event.host_id == current_user.id
                    })
    
    return jsonify(calendar_events)

# Import routes to register them
if __name__ != '__main__':
    import routes
