from datetime import datetime, date, timedelta
from urllib.parse import urlparse, urljoin
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Show, ShowInstance, Signup, ShowRunner, ShowHost, ShowInstanceHost
from forms import RegistrationForm, LoginForm, EventForm, SignupForm, CancellationForm


def is_safe_url(target):
    """Check if the target URL is safe for redirects (same domain only)."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        user.set_password(form.password.data)
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
                next_page = url_for('dashboard')
            return redirect(next_page)
        flash('Invalid username or password')
    
    return render_template('auth/login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Combined dashboard that shows relevant content based on user's roles"""
    # Get all shows where user has any role
    owned_shows = Show.query.filter_by(owner_id=current_user.id, is_deleted=False).all()
    
    # Get shows where user is a runner or host
    runner_show_ids = [sr.show_id for sr in current_user.show_runner_roles]
    host_show_ids = [sh.show_id for sh in current_user.show_host_roles]
    
    managed_shows = []
    if runner_show_ids or host_show_ids:
        all_managed_ids = list(set(runner_show_ids + host_show_ids))
        managed_shows = Show.query.filter(
            Show.id.in_(all_managed_ids),
            Show.is_deleted == False
        ).all()
    
    # Get upcoming show instances for shows user can manage
    all_show_ids = [s.id for s in owned_shows + managed_shows]
    upcoming_instances = []
    if all_show_ids:
        upcoming_instances = ShowInstance.query.filter(
            ShowInstance.show_id.in_(all_show_ids),
            ShowInstance.instance_date >= date.today(),
            ShowInstance.is_cancelled == False
        ).order_by(ShowInstance.instance_date).limit(10).all()
    
    # Get user's recent signups
    recent_signups = Signup.query.filter_by(comedian_id=current_user.id)\
        .join(ShowInstance)\
        .filter(ShowInstance.instance_date >= date.today())\
        .order_by(ShowInstance.instance_date)\
        .limit(5).all()
    
    return render_template('combined_dashboard.html', 
                         owned_shows=owned_shows,
                         managed_shows=managed_shows,
                         upcoming_instances=upcoming_instances,
                         recent_signups=recent_signups)


@app.route('/calendar')
@login_required
def calendar_view():
    """Calendar view showing upcoming show instances"""
    return render_template('calendar.html')


@app.route('/api/calendar/events')
@login_required
def calendar_events_api():
    """API endpoint to get calendar events for the calendar view"""
    try:
        # Get upcoming show instances (next 3 months)
        start_date = date.today()
        end_date = start_date + timedelta(days=90)
        
        instances = ShowInstance.query.join(Show).filter(
            Show.is_deleted == False,
            ShowInstance.instance_date >= start_date,
            ShowInstance.instance_date <= end_date,
            ShowInstance.is_cancelled == False
        ).order_by(ShowInstance.instance_date).all()
        
        events = []
        for instance in instances:
            events.append({
                'id': instance.id,
                'title': f"{instance.show.name} @ {instance.show.venue}",
                'date': instance.instance_date.isoformat(),
                'url': url_for('event_info', event_id=instance.id),
                'backgroundColor': '#007bff',
                'borderColor': '#007bff'
            })
        
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/event/<int:event_id>')
def event_info(event_id):
    """Show information about a specific show instance"""
    instance = ShowInstance.query.get_or_404(event_id)
    signups = Signup.query.filter_by(show_instance_id=instance.id).order_by(Signup.signup_time).all()
    
    return render_template('public/event_info.html', 
                         event=instance, 
                         signups=signups)


@app.route('/live/<int:event_id>')
def live_lineup(event_id):
    """Live lineup view for show instances"""
    instance = ShowInstance.query.get_or_404(event_id)
    signups = Signup.query.filter_by(show_instance_id=instance.id)\
                    .order_by(Signup.position.asc().nullslast(), Signup.signup_time).all()
    
    return render_template('public/live_lineup.html', 
                         event=instance, 
                         signups=signups)