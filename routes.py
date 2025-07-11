from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import app, db
from forms import (
    CancellationForm,
    EventForm,
    InstanceHostForm,
    LoginForm,
    RegistrationForm,
    ShowSettingsForm,
    SignupForm,
)
from models import (
    Show,
    ShowHost,
    ShowInstance,
    ShowInstanceHost,
    ShowRunner,
    Signup,
    User,
)


def is_safe_url(target):
    """Check if the target URL is safe for redirects (same domain only)."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@app.route("/")
def index():
    if current_user.is_authenticated:
        # Unified dashboard for logged-in users
        
        # My Next Set - next event user is signed up for
        next_signup = (
            Signup.query.filter_by(comedian_id=current_user.id)
            .join(ShowInstance)
            .filter(ShowInstance.instance_date >= date.today())
            .order_by(ShowInstance.instance_date)
            .first()
        )
        
        # My Open Mics - shows owned by user (hide if empty)
        owned_shows = Show.query.filter_by(owner_id=current_user.id, is_deleted=False).all()
        
        # Get upcoming instances for owned shows
        owned_show_instances = []
        if owned_shows:
            owned_show_ids = [show.id for show in owned_shows]
            owned_show_instances = (
                ShowInstance.query.filter(
                    ShowInstance.show_id.in_(owned_show_ids),
                    ShowInstance.instance_date >= date.today(),
                    ShowInstance.is_cancelled == False,
                )
                .order_by(ShowInstance.instance_date)
                .limit(5)
                .all()
            )
        
        # Your Upcoming Performances - user's signups
        upcoming_performances = (
            Signup.query.filter_by(comedian_id=current_user.id)
            .join(ShowInstance)
            .filter(ShowInstance.instance_date >= date.today())
            .order_by(ShowInstance.instance_date)
            .limit(5)
            .all()
        )
        
        return render_template(
            "unified_dashboard.html",
            next_signup=next_signup,
            owned_shows=owned_shows,
            owned_show_instances=owned_show_instances,
            upcoming_performances=upcoming_performances,
        )
    else:
        # Public landing page for non-authenticated users
        # Get today's events for sidebar
        events_today = (
            ShowInstance.query.join(Show)
            .filter(
                Show.is_deleted == False,
                ShowInstance.instance_date == date.today(),
                ShowInstance.is_cancelled == False,
            )
            .order_by(Show.start_time)
            .all()
        )
        
        return render_template("index.html", events_today=events_today)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! You can now log in.")
        return redirect(url_for("login"))

    return render_template("auth/register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            if not next_page or not is_safe_url(next_page):
                next_page = url_for("dashboard")
            return redirect(next_page)
        flash("Invalid username or password")

    return render_template("auth/login.html", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
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
            Show.id.in_(all_managed_ids), Show.is_deleted == False
        ).all()

    # Get upcoming show instances for shows user can manage
    all_show_ids = [s.id for s in owned_shows + managed_shows]
    upcoming_instances = []
    if all_show_ids:
        upcoming_instances = (
            ShowInstance.query.filter(
                ShowInstance.show_id.in_(all_show_ids),
                ShowInstance.instance_date >= date.today(),
                ShowInstance.is_cancelled == False,
            )
            .order_by(ShowInstance.instance_date)
            .limit(10)
            .all()
        )

    # Get user's recent signups
    recent_signups = (
        Signup.query.filter_by(comedian_id=current_user.id)
        .join(ShowInstance)
        .filter(ShowInstance.instance_date >= date.today())
        .order_by(ShowInstance.instance_date)
        .limit(5)
        .all()
    )

    return render_template(
        "combined_dashboard.html",
        owned_shows=owned_shows,
        managed_shows=managed_shows,
        upcoming_instances=upcoming_instances,
        recent_signups=recent_signups,
    )


@app.route("/comedian/dashboard")
@login_required
def comedian_dashboard():
    """Comedian-specific dashboard showing available shows to sign up for"""
    # Get upcoming show instances within the next month
    one_month_from_now = date.today() + timedelta(days=30)
    upcoming_instances = (
        ShowInstance.query.join(Show)
        .filter(
            Show.is_deleted == False,
            ShowInstance.instance_date >= date.today(),
            ShowInstance.instance_date <= one_month_from_now,
            ShowInstance.is_cancelled == False,
        )
        .order_by(ShowInstance.instance_date)
        .all()
    )

    # Get user's current signups with show instance data
    upcoming_signups = (
        Signup.query.filter_by(comedian_id=current_user.id)
        .join(ShowInstance)
        .filter(ShowInstance.instance_date >= date.today())
        .order_by(ShowInstance.instance_date)
        .all()
    )

    signup_instance_ids = [signup.show_instance_id for signup in upcoming_signups]

    return render_template(
        "comedian/dashboard.html",
        events=upcoming_instances,
        upcoming_signups=upcoming_signups,
        signup_event_ids=signup_instance_ids,
    )


@app.route("/host/dashboard")
@login_required
def host_dashboard():
    """Host-specific dashboard for managing shows and lineups"""
    import os
    # Get shows user can manage
    owned_shows = Show.query.filter_by(owner_id=current_user.id, is_deleted=False).all()

    # Get shows where user is a runner or host
    runner_show_ids = [sr.show_id for sr in current_user.show_runner_roles]
    host_show_ids = [sh.show_id for sh in current_user.show_host_roles]

    managed_shows = []
    if runner_show_ids or host_show_ids:
        all_managed_ids = list(set(runner_show_ids + host_show_ids))
        managed_shows = Show.query.filter(
            Show.id.in_(all_managed_ids), Show.is_deleted == False
        ).all()

    all_shows = owned_shows + managed_shows

    return render_template(
        "host/dashboard.html",
        events=all_shows,  # Use 'events' to match template expectations
        owned_shows=owned_shows,
        managed_shows=managed_shows,
        all_shows=all_shows,
        google_maps_api_key=os.environ.get("GOOGLE_MAPS_API_KEY", ""),
    )


@app.route("/host/upcoming_lineups/<int:show_id>")
@login_required
def upcoming_lineups(show_id):
    """View upcoming lineups for a specific show"""
    show = Show.query.get_or_404(show_id)

    # Check if user can manage this show
    if not current_user.can_manage_lineup(show):
        flash("You don't have permission to manage this show.", "error")
        return redirect(url_for("host_dashboard"))

    # Get upcoming instances (next 10 instances)
    from datetime import date, timedelta

    upcoming_instances = (
        ShowInstance.query.filter(ShowInstance.show_id == show_id)
        .filter(ShowInstance.instance_date >= date.today())
        .order_by(ShowInstance.instance_date.asc())
        .limit(10)
        .all()
    )

    return render_template(
        "host/upcoming_lineups.html", show=show, upcoming_instances=upcoming_instances
    )


@app.route("/cancel_show_instance/<int:instance_id>", methods=["POST"])
@login_required
def cancel_show_instance(instance_id):
    """Cancel a specific show instance"""
    instance = ShowInstance.query.get_or_404(instance_id)

    # Check permissions
    if not current_user.can_manage_lineup(instance.show):
        return jsonify({"success": False, "error": "Permission denied"}), 403

    reason = request.json.get("reason", "") if request.is_json else ""
    instance.cancel(reason)
    db.session.commit()

    return jsonify({"success": True, "message": "Show cancelled successfully"})


@app.route("/restore_show_instance/<int:instance_id>", methods=["POST"])
@login_required
def restore_show_instance(instance_id):
    """Restore a cancelled show instance"""
    instance = ShowInstance.query.get_or_404(instance_id)

    # Check permissions
    if not current_user.can_manage_lineup(instance.show):
        return jsonify({"success": False, "error": "Permission denied"}), 403

    instance.uncancel()
    db.session.commit()

    return jsonify({"success": True, "message": "Show restored successfully"})


@app.route("/api/show/<int:show_id>", methods=["GET"])
@login_required
def get_show_data(show_id):
    """Get show data for editing"""
    show = Show.query.get_or_404(show_id)

    # Check permissions
    if not current_user.can_edit_show(show):
        return jsonify({"success": False, "error": "Permission denied"}), 403

    # Convert signup timing back to display format
    signups_open_value, signups_open_unit = Show.convert_minutes_to_time_unit(show.signups_open)
    signups_closed_value, signups_closed_unit = Show.convert_minutes_to_time_unit(show.signups_closed)
    
    return jsonify(
        {
            "id": show.id,
            "name": show.name,
            "venue": show.venue,
            "address": show.address,
            "timezone": show.timezone,
            "day_of_week": show.day_of_week,
            "start_time": show.start_time.strftime("%H:%M") if show.start_time else "",
            "end_time": show.end_time.strftime("%H:%M") if show.end_time else "",
            "description": show.description or "",
            "max_signups": show.max_signups,
            "signups_open_value": signups_open_value,
            "signups_open_unit": signups_open_unit,
            "signups_closed_value": signups_closed_value,
            "signups_closed_unit": signups_closed_unit,
            "signup_deadline_hours": show.signup_window_after_hours,  # Keep for compatibility
            "show_host_info": show.show_host_info,
            "show_owner_info": show.show_owner_info,
        }
    )


@app.route("/api/show", methods=["POST"])
@login_required
def create_show_api():
    """Create a new show via API"""
    data = request.get_json()

    # Validate required fields
    required_fields = [
        "name",
        "venue",
        "address",
        "day_of_week",
        "start_time",
        "max_signups",
        "signup_deadline_hours",
    ]
    for field in required_fields:
        if not data.get(field):
            return (
                jsonify(
                    {"success": False, "error": f"Missing required field: {field}"}
                ),
                400,
            )

    try:
        # Create new show - times are in the event's local timezone
        from app import local_to_utc
        
        # Parse times and convert to UTC for storage
        start_time_str = data["start_time"]
        end_time_str = data.get("end_time")
        event_timezone = data.get("timezone", "America/New_York")  # Get timezone from form
        
        # Convert time strings to datetime objects in event timezone, then to UTC
        start_dt = datetime.strptime(f"2000-01-01 {start_time_str}", "%Y-%m-%d %H:%M")
        start_time_utc = local_to_utc(start_dt, event_timezone).time()
        
        end_time_utc = None
        if end_time_str:
            end_dt = datetime.strptime(f"2000-01-01 {end_time_str}", "%Y-%m-%d %H:%M")
            end_time_utc = local_to_utc(end_dt, event_timezone).time()
        
        # Convert signup timing to minutes
        signups_open_minutes = Show.convert_time_to_minutes(
            data.get("signups_open_value", 2), 
            data.get("signups_open_unit", "days")
        )
        signups_closed_minutes = Show.convert_time_to_minutes(
            data.get("signups_closed_value", 0), 
            data.get("signups_closed_unit", "minutes")
        )
        
        show = Show(
            name=data["name"],
            venue=data["venue"],
            address=data["address"],
            timezone=event_timezone,
            description=data.get("description", ""),
            day_of_week=data["day_of_week"],
            start_time=start_time_utc,
            end_time=end_time_utc,
            max_signups=data["max_signups"],
            signups_open=signups_open_minutes,
            signups_closed=signups_closed_minutes,
            signup_window_after_hours=data.get("signup_deadline_hours", 2),  # Keep for backward compatibility
            owner_id=current_user.id,
            default_host_id=current_user.id,
            show_host_info=data.get("show_host_info", True),
            show_owner_info=data.get("show_owner_info", False),
        )
        db.session.add(show)
        db.session.flush()  # Get the show ID

        # Create show instances for the next 3 months
        from datetime import timedelta

        start_date = show.get_next_instance_date()
        end_date = start_date + timedelta(days=90)

        # Create instances more efficiently with simple logic
        instances = []
        current_date = start_date
        instance_count = 0
        
        while current_date <= end_date and instance_count < 20:  # Limit to 20 instances (~5 months)
            instances.append(ShowInstance(show_id=show.id, instance_date=current_date))
            
            # Simple weekly increment for now to avoid complex date calculations
            if show.repeat_cadence == "bi-weekly":
                current_date += timedelta(days=14)
            elif show.repeat_cadence == "monthly":
                # Add roughly 4 weeks for monthly
                current_date += timedelta(days=28)
            elif show.repeat_cadence == "custom" and show.custom_repeat_days:
                current_date += timedelta(days=show.custom_repeat_days)
            else:
                # Default weekly
                current_date += timedelta(days=7)
            
            instance_count += 1
        
        # Add all instances at once
        db.session.add_all(instances)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Successfully created {show.name}!",
                "show_id": show.id,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/show/<int:show_id>", methods=["PUT"])
@login_required
def update_show_api(show_id):
    """Update an existing show via API"""
    show = Show.query.get_or_404(show_id)

    # Check permissions
    if not current_user.can_edit_show(show):
        return jsonify({"success": False, "error": "Permission denied"}), 403

    data = request.get_json()

    try:
        # Update show fields
        if "name" in data:
            show.name = data["name"]
        if "venue" in data:
            show.venue = data["venue"]
        if "address" in data:
            show.address = data["address"]
        if "description" in data:
            show.description = data["description"]
        if "day_of_week" in data:
            show.day_of_week = data["day_of_week"]
        if "start_time" in data:
            show.start_time = datetime.strptime(data["start_time"], "%H:%M").time()
        if "end_time" in data:
            show.end_time = (
                datetime.strptime(data["end_time"], "%H:%M").time()
                if data["end_time"]
                else None
            )
        if "max_signups" in data:
            show.max_signups = data["max_signups"]
        if "signup_deadline_hours" in data:
            show.signup_window_after_hours = data["signup_deadline_hours"]
        
        # Handle new signup timing fields
        if "signups_open_value" in data and "signups_open_unit" in data:
            show.signups_open = Show.convert_time_to_minutes(
                data["signups_open_value"], 
                data["signups_open_unit"]
            )
        if "signups_closed_value" in data and "signups_closed_unit" in data:
            show.signups_closed = Show.convert_time_to_minutes(
                data["signups_closed_value"], 
                data["signups_closed_unit"]
            )
        
        if "show_host_info" in data:
            show.show_host_info = data["show_host_info"]
        if "show_owner_info" in data:
            show.show_owner_info = data["show_owner_info"]

        show.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Successfully updated {show.name}!",
                "show_id": show.id,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/host/create-event", methods=["GET", "POST"])
@login_required
def create_event():
    """Create a new recurring show"""
    form = EventForm()
    if form.validate_on_submit():
        # Convert signup timing to minutes
        signups_open_minutes = Show.convert_time_to_minutes(
            form.signups_open_value.data, form.signups_open_unit.data
        )
        signups_closed_minutes = Show.convert_time_to_minutes(
            form.signups_closed_value.data, form.signups_closed_unit.data
        )
        
        # Create new show
        show = Show(
            name=form.name.data,
            venue=form.venue.data,
            address=form.address.data,
            description=form.description.data,
            day_of_week=form.day_of_week.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            max_signups=form.max_signups.data,
            signups_open=signups_open_minutes,
            signups_closed=signups_closed_minutes,
            signup_window_after_hours=form.signup_deadline_hours.data,  # Keep for backward compatibility
            owner_id=current_user.id,
            default_host_id=current_user.id,
            show_host_info=form.show_host_info.data,
            show_owner_info=form.show_owner_info.data,
        )
        db.session.add(show)
        db.session.flush()  # Get the show ID

        # Create show instances for the next 3 months
        from datetime import timedelta

        current_date = date.today()
        end_date = current_date + timedelta(days=90)  # 3 months ahead

        # Find the next occurrence of this day of week
        target_date = show.get_next_instance_date(current_date)

        while target_date and target_date <= end_date:
            # Check if instance already exists
            existing_instance = ShowInstance.query.filter_by(
                show_id=show.id, instance_date=target_date
            ).first()

            if not existing_instance:
                instance = ShowInstance(show_id=show.id, instance_date=target_date)
                db.session.add(instance)

            # Get next occurrence based on repeat cadence
            target_date = show.get_next_instance_date(target_date + timedelta(days=1))

        db.session.commit()

        flash("Show created successfully!")
        return redirect(url_for("host_dashboard"))

    return render_template("host/create_event.html", form=form, GOOGLE_MAPS_API_KEY=os.environ.get('GOOGLE_MAPS_API_KEY'))


@app.route("/host/show/<int:show_id>/settings", methods=["GET", "POST"])
@login_required
def show_settings(show_id):
    """Edit show settings including host management"""
    from forms import ShowSettingsForm

    show = Show.query.get_or_404(show_id)

    # Check permissions
    if not current_user.can_edit_show(show):
        flash("Access denied.")
        return redirect(url_for("host_dashboard"))

    form = ShowSettingsForm(show=show)

    if form.validate_on_submit():
        # Update default host
        if form.default_host_id.data == 0:
            show.default_host_id = None
        else:
            show.default_host_id = form.default_host_id.data

        # Update display settings
        show.show_host_info = form.show_host_info.data
        show.show_owner_info = form.show_owner_info.data

        db.session.commit()
        flash("Show settings updated successfully!")
        return redirect(url_for("host_dashboard"))

    # Pre-populate form with current values
    form.default_host_id.data = show.default_host_id or 0
    form.show_host_info.data = show.show_host_info
    form.show_owner_info.data = show.show_owner_info

    return render_template("host/show_settings.html", form=form, show=show)


@app.route("/host/instance/<int:instance_id>/host", methods=["GET", "POST"])
@login_required
def manage_instance_host(instance_id):
    """Assign host to specific show instance"""
    from forms import InstanceHostForm
    from models import ShowInstanceHost

    instance = ShowInstance.query.get_or_404(instance_id)

    # Check permissions
    if not current_user.can_manage_lineup(instance.show):
        flash("Access denied.")
        return redirect(url_for("calendar_view"))

    form = InstanceHostForm(show=instance.show)

    if form.validate_on_submit():
        # Remove existing instance host
        existing_host = ShowInstanceHost.query.filter_by(
            show_instance_id=instance_id
        ).first()
        if existing_host:
            db.session.delete(existing_host)

        # Add new instance host
        new_host = ShowInstanceHost(
            show_instance_id=instance_id, user_id=form.host_id.data
        )
        db.session.add(new_host)
        db.session.commit()

        flash("Instance host assigned successfully!")
        return redirect(url_for("calendar_view"))

    # Pre-populate with current instance host if exists
    current_host = ShowInstanceHost.query.filter_by(
        show_instance_id=instance_id
    ).first()
    if current_host:
        form.host_id.data = current_host.user_id

    return render_template("host/instance_host.html", form=form, instance=instance)


@app.route("/calendar")
@login_required
def calendar_view():
    """Calendar view showing upcoming show instances"""
    # Get requested year/month or default to current
    today = date.today()
    current_year = request.args.get("year", default=today.year, type=int)
    current_month = request.args.get("month", default=today.month, type=int)

    # Calculate previous and next month for navigation
    if current_month == 1:
        prev_month = date(current_year - 1, 12, 1)
    else:
        prev_month = date(current_year, current_month - 1, 1)

    if current_month == 12:
        next_month = date(current_year + 1, 1, 1)
    else:
        next_month = date(current_year, current_month + 1, 1)

    # Get show instances for the requested month
    month_start = date(current_year, current_month, 1)
    if current_month == 12:
        next_month_start = date(current_year + 1, 1, 1)
    else:
        next_month_start = date(current_year, current_month + 1, 1)

    instances = (
        ShowInstance.query.join(Show)
        .filter(
            Show.is_deleted == False,
            ShowInstance.instance_date >= month_start,
            ShowInstance.instance_date < next_month_start,
            ShowInstance.is_cancelled == False,
        )
        .order_by(ShowInstance.instance_date)
        .all()
    )

    # Group events by date for template
    events_by_date = {}
    for instance in instances:
        instance_date = instance.instance_date
        if instance_date not in events_by_date:
            events_by_date[instance_date] = []

        # Get signup count
        signup_count = Signup.query.filter_by(show_instance_id=instance.id).count()

        # Determine color based on user's relationship to event
        background_color = "#6c757d"  # Default dull gray
        color_class = "default-event"

        if current_user.is_authenticated:
            # Check if user owns the event
            if instance.show.owner_id == current_user.id:
                background_color = "#dc3545"  # Red for owned events
                color_class = "owned-event"
            else:
                # Check if user has signed up for this event
                user_signup = Signup.query.filter_by(
                    comedian_id=current_user.id, show_instance_id=instance.id
                ).first()

                if user_signup:
                    background_color = "#28a745"  # Green for signed up events
                    color_class = "signed-up-event"

        events_by_date[instance_date].append(
            {
                "event": instance,
                "date": instance_date,
                "signup_count": signup_count,
                "background_color": background_color,
                "color_class": color_class,
            }
        )

    # Generate calendar days for the requested month
    import calendar

    cal = calendar.monthcalendar(current_year, current_month)

    return render_template(
        "calendar.html",
        current_year=current_year,
        current_month=date(current_year, current_month, 1),
        prev_month=prev_month,
        next_month=next_month,
        events_by_date=events_by_date,
        month_days=cal,
        today=today,
    )


@app.route("/api/calendar/events")
@login_required
def calendar_events_api():
    """API endpoint to get calendar events for the calendar view"""
    try:
        # Get upcoming show instances (next 3 months)
        start_date = date.today()
        end_date = start_date + timedelta(days=90)

        instances = (
            ShowInstance.query.join(Show)
            .filter(
                Show.is_deleted == False,
                ShowInstance.instance_date >= start_date,
                ShowInstance.instance_date <= end_date,
                ShowInstance.is_cancelled == False,
            )
            .order_by(ShowInstance.instance_date)
            .all()
        )

        events = []
        for instance in instances:
            # Determine color based on user's relationship to event
            background_color = "#6c757d"  # Default dull blue/gray
            border_color = "#6c757d"

            if current_user.is_authenticated:
                # Check if user owns the event
                if instance.show.owner_id == current_user.id:
                    background_color = "#dc3545"  # Red for owned events
                    border_color = "#dc3545"
                else:
                    # Check if user has signed up for this event
                    user_signup = Signup.query.filter_by(
                        comedian_id=current_user.id, show_instance_id=instance.id
                    ).first()

                    if user_signup:
                        background_color = "#28a745"  # Green for signed up events
                        border_color = "#28a745"

            events.append(
                {
                    "id": instance.id,
                    "title": f"{instance.show.name} @ {instance.show.venue}",
                    "date": instance.instance_date.isoformat(),
                    "url": url_for("event_info", event_id=instance.id),
                    "backgroundColor": background_color,
                    "borderColor": border_color,
                }
            )

        return jsonify(events)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/event/<int:event_id>")
def event_info(event_id):
    """Show information about a specific show instance"""
    instance = ShowInstance.query.get_or_404(event_id)
    signups = (
        Signup.query.filter_by(show_instance_id=instance.id)
        .order_by(Signup.signup_time)
        .all()
    )

    return render_template("public/event_info.html", event=instance, signups=signups)


@app.route("/live/<int:event_id>")
def live_lineup(event_id):
    """Live lineup view for show instances"""
    instance = ShowInstance.query.get_or_404(event_id)
    signups = (
        Signup.query.filter_by(show_instance_id=instance.id)
        .order_by(Signup.position.asc().nullslast(), Signup.signup_time)
        .all()
    )

    from datetime import datetime

    return render_template(
        "public/live_lineup.html",
        event=instance,
        signups=signups,
        current_time=datetime.now(),
    )


@app.route("/signup/<int:event_id>", methods=["GET", "POST"])
@login_required
def signup_for_event(event_id):
    """Allow comedians and hosts to sign up for show instances"""
    instance = ShowInstance.query.get_or_404(event_id)

    # Check if show instance is cancelled
    if instance.is_cancelled:
        flash("This show is cancelled.", "error")
        referrer = request.referrer
        if referrer and "calendar" in referrer:
            return redirect(url_for("calendar_view"))
        elif referrer and "comedian" in referrer:
            return redirect(url_for("comedian_dashboard"))
        else:
            return redirect(url_for("comedian_dashboard"))

    # Check if user is already signed up
    existing_signup = Signup.query.filter_by(
        comedian_id=current_user.id, show_instance_id=instance.id
    ).first()

    if existing_signup:
        flash("You are already signed up for this show.", "warning")
        referrer = request.referrer
        if referrer and "calendar" in referrer:
            return redirect(url_for("calendar_view"))
        elif referrer and "comedian" in referrer:
            return redirect(url_for("comedian_dashboard"))
        else:
            return redirect(url_for("comedian_dashboard"))

    form = SignupForm()

    if form.validate_on_submit():
        # Check if signups are still open
        from datetime import datetime, timedelta

        show_datetime = datetime.combine(instance.instance_date, instance.start_time)
        signup_deadline = show_datetime - timedelta(
            hours=instance.show.signup_window_after_hours
        )

        if datetime.now() > signup_deadline:
            flash("Signup deadline has passed for this show.", "error")
            referrer = request.referrer
            if referrer and "calendar" in referrer:
                return redirect(url_for("calendar_view"))
            elif referrer and "comedian" in referrer:
                return redirect(url_for("comedian_dashboard"))
            else:
                return redirect(url_for("comedian_dashboard"))

        # Check if show is full
        current_signups = Signup.query.filter_by(show_instance_id=instance.id).count()
        if current_signups >= instance.max_signups:
            flash("This show is full.", "error")
            referrer = request.referrer
            if referrer and "calendar" in referrer:
                return redirect(url_for("calendar_view"))
            elif referrer and "comedian" in referrer:
                return redirect(url_for("comedian_dashboard"))
            else:
                return redirect(url_for("comedian_dashboard"))

        # Create signup
        signup = Signup(
            comedian_id=current_user.id,
            show_instance_id=instance.id,
            notes=form.notes.data,
        )
        db.session.add(signup)
        db.session.commit()

        flash(f"Successfully signed up for {instance.show.name}!", "success")

        # Redirect based on referrer
        referrer = request.referrer
        if referrer and "calendar" in referrer:
            return redirect(url_for("calendar_view"))
        elif referrer and "comedian" in referrer:
            return redirect(url_for("comedian_dashboard"))
        else:
            return redirect(url_for("comedian_dashboard"))

    # Handle AJAX requests for modal
    if request.headers.get("Content-Type") == "application/json":
        return jsonify(
            {
                "event_name": instance.show.name,
                "event_date": instance.instance_date.strftime("%A, %B %d, %Y"),
                "event_time": instance.start_time.strftime("%I:%M %p"),
                "venue": instance.show.venue,
                "signups": Signup.query.filter_by(show_instance_id=instance.id).count(),
                "max_signups": instance.max_signups,
            }
        )

    return render_template("comedian/signup.html", form=form, event=instance)


@app.route("/api/signup/<int:event_id>", methods=["POST"])
@login_required
def api_signup_for_event(event_id):
    """AJAX endpoint for signing up for events"""
    instance = ShowInstance.query.get_or_404(event_id)

    # Check if show instance is cancelled
    if instance.is_cancelled:
        return jsonify({"success": False, "error": "This show is cancelled."}), 400

    # Check if user is already signed up
    existing_signup = Signup.query.filter_by(
        comedian_id=current_user.id, show_instance_id=instance.id
    ).first()

    if existing_signup:
        return (
            jsonify(
                {"success": False, "error": "You are already signed up for this show."}
            ),
            400,
        )

    # Check if signups are still open
    from datetime import datetime, timedelta

    show_datetime = datetime.combine(instance.instance_date, instance.start_time)
    signup_deadline = show_datetime - timedelta(
        hours=instance.show.signup_window_after_hours
    )

    if datetime.now() > signup_deadline:
        return (
            jsonify(
                {"success": False, "error": "Signup deadline has passed for this show."}
            ),
            400,
        )

    # Check if show is full
    current_signups = Signup.query.filter_by(show_instance_id=instance.id).count()
    if current_signups >= instance.max_signups:
        return jsonify({"success": False, "error": "This show is full."}), 400

    # Get notes from request
    notes = request.json.get("notes", "") if request.is_json else ""

    # Create signup
    signup = Signup(
        comedian_id=current_user.id, show_instance_id=instance.id, notes=notes
    )
    db.session.add(signup)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"Successfully signed up for {instance.show.name}!",
            "signup_count": current_signups + 1,
        }
    )


@app.route("/cancel_signup/<int:signup_id>", methods=["POST"])
@login_required
def cancel_signup(signup_id):
    """Allow comedians to cancel their own signups or hosts to remove signups"""
    signup = Signup.query.get_or_404(signup_id)

    # Check if user owns this signup or can manage the show
    can_cancel = (
        signup.comedian_id == current_user.id
        or current_user.can_manage_lineup(signup.show_instance.show)
    )

    if not can_cancel:
        flash("You can only cancel your own signups.", "error")
        return redirect(url_for("dashboard"))

    show_name = signup.show_instance.show.name
    comedian_name = signup.comedian.full_name if signup.comedian else "Guest"

    db.session.delete(signup)
    db.session.commit()

    if signup.comedian_id == current_user.id:
        flash(f"Cancelled your signup for {show_name}.", "success")
        return redirect(url_for("comedian_dashboard"))
    else:
        flash(f"Removed {comedian_name} from {show_name}.", "success")
        return redirect(url_for("manage_lineup", event_id=signup.show_instance.id))


@app.route("/manage_lineup/<int:event_id>", methods=["GET", "POST"])
@login_required
def manage_lineup(event_id):
    """Allow hosts to manage show lineup and manually add comedians"""
    instance = ShowInstance.query.get_or_404(event_id)

    # Check if user can manage this show
    if not current_user.can_manage_lineup(instance.show):
        flash("You don't have permission to manage this show's lineup.", "error")
        return redirect(url_for("dashboard"))

    # Get signups ordered by position then signup time
    signups = (
        Signup.query.filter_by(show_instance_id=instance.id)
        .order_by(Signup.position.asc().nullslast(), Signup.signup_time)
        .all()
    )

    # Handle position updates
    if request.method == "POST":
        if "update_positions" in request.form:
            # Update positions from form data
            for signup in signups:
                position_key = f"position_{signup.id}"
                if position_key in request.form:
                    new_position = request.form[position_key]
                    signup.position = int(new_position) if new_position else None

            db.session.commit()
            flash("Lineup positions updated.", "success")
            return redirect(url_for("manage_lineup", event_id=event_id))

        elif "add_comedian" in request.form:
            # Add comedian manually
            comedian_name = request.form.get("comedian_name", "").strip()
            if comedian_name:
                # Try to find existing user first
                comedian = User.query.filter_by(username=comedian_name).first()
                if not comedian:
                    # Create a note-based signup for non-registered comedian
                    signup = Signup(
                        comedian_id=None,  # No user account
                        show_instance_id=instance.id,
                        notes=f"Host added: {comedian_name}",
                    )
                    db.session.add(signup)
                    db.session.commit()
                    flash(f"Added {comedian_name} to the lineup.", "success")
                else:
                    # Check if already signed up
                    existing = Signup.query.filter_by(
                        comedian_id=comedian.id, show_instance_id=instance.id
                    ).first()
                    if existing:
                        flash(f"{comedian_name} is already signed up.", "warning")
                    else:
                        signup = Signup(
                            comedian_id=comedian.id,
                            show_instance_id=instance.id,
                            notes="Added by host",
                        )
                        db.session.add(signup)
                        db.session.commit()
                        flash(f"Added {comedian_name} to the lineup.", "success")

            return redirect(url_for("manage_lineup", event_id=event_id))

    return render_template("host/manage_lineup.html", event=instance, signups=signups)


@app.route("/host/reorder_lineup/<int:event_id>", methods=["POST"])
@login_required
def reorder_lineup(event_id):
    """Handle drag-and-drop reordering of lineup positions"""
    instance = ShowInstance.query.get_or_404(event_id)

    # Check if user can manage this show
    if not current_user.can_manage_lineup(instance.show):
        return jsonify({"success": False, "error": "Permission denied"}), 403

    try:
        data = request.get_json()
        signup_ids = data.get("signup_ids", [])

        # Update positions based on order
        for position, signup_id in enumerate(signup_ids, 1):
            signup = Signup.query.get(signup_id)
            if signup and signup.show_instance_id == instance.id:
                signup.position = position

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
