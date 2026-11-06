"""
Hostel Management System - Main Flask Application
Developed with Python Flask, SQLite, and Jinja2.
"""

import os
import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g, abort, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, close_connection, query_db, modify_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hostel_management_super_secret_key_2026')
app.teardown_appcontext(close_connection)


# -------------------------------------------------------------
# Template Filters & Context Processors
# -------------------------------------------------------------
@app.context_processor
def inject_globals():
    """Inject current user and current year into all templates."""
    user = None
    if 'user_id' in session:
        user = query_db("SELECT * FROM users WHERE id = ?", (session['user_id'],), one=True)
    
    # Days of week for mess navigation
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today_name = datetime.datetime.now().strftime('%A')
    
    return {
        'current_user': user,
        'current_year': datetime.datetime.now().year,
        'days_of_week': days,
        'today_name': today_name
    }


@app.template_filter('format_datetime')
def format_datetime(value, format_str='%d %b %Y, %I:%M %p'):
    """Format a SQLite timestamp string into a readable date/time."""
    if not value:
        return 'N/A'
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            dt = datetime.datetime.strptime(str(value).split('.')[0], fmt)
            return dt.strftime(format_str)
        except ValueError:
            pass
    return str(value)


@app.template_filter('time_ago')
def time_ago(value):
    """Return friendly relative time (e.g. '2 hours ago')."""
    if not value:
        return ''
    try:
        dt = datetime.datetime.strptime(str(value).split('.')[0], '%Y-%m-%d %H:%M:%S')
        now = datetime.datetime.now()
        diff = now - dt
        if diff.days > 30:
            return dt.strftime('%d %b %Y')
        if diff.days > 0:
            return f"{diff.days}d ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = diff.seconds // 60
        if minutes > 0:
            return f"{minutes}m ago"
        return "Just now"
    except Exception:
        return str(value)


# -------------------------------------------------------------
# Auth Decorators
# -------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Administrator login required.", "warning")
            return redirect(url_for('login', next=request.path))
        if session.get('role') != 'admin':
            flash("Access denied: Administrative privileges required.", "danger")
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Student login required.", "warning")
            return redirect(url_for('login', next=request.path))
        if session.get('role') != 'student':
            flash("Access denied: Student account required.", "danger")
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------
# Public & Authentication Routes
# -------------------------------------------------------------
@app.route('/')
def index():
    """Landing page featuring overview, quick stats, notices, and today's mess menu."""
    today = datetime.datetime.now().strftime('%A')
    
    # Fetch recent notices
    notices = query_db("""
        SELECT n.*, u.full_name as author_name
        FROM notices n
        JOIN users u ON n.created_by = u.id
        ORDER BY n.is_pinned DESC, n.created_at DESC
        LIMIT 4
    """)
    
    # Fetch today's meals
    today_meals = query_db("""
        SELECT * FROM mess_menu 
        WHERE day_of_week = ?
        ORDER BY 
            CASE meal_type 
                WHEN 'Breakfast' THEN 1 
                WHEN 'Lunch' THEN 2 
                WHEN 'Snacks' THEN 3 
                WHEN 'Dinner' THEN 4 
            END
    """, (today,))
    
    # Hostel stats
    stats = {
        'total_rooms': query_db("SELECT COUNT(*) as c FROM rooms", one=True)['c'],
        'total_students': query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student'", one=True)['c'],
        'resolved_complaints': query_db("SELECT COUNT(*) as c FROM complaints WHERE status = 'Resolved'", one=True)['c']
    }
    
    return render_template('index.html', notices=notices, today_meals=today_meals, today=today, stats=stats)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login for both students and administrators."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash("Please enter both username/roll number and password.", "danger")
            return render_template('login.html', username=username)

        user = query_db("SELECT * FROM users WHERE username = ? OR email = ?", (username, username), one=True)
        
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            flash(f"Welcome back, {user['full_name']}!", "success")
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid credentials. Please verify your roll number/username and password.", "danger")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration page."""
    if 'user_id' in session:
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        guardian_name = request.form.get('guardian_name', '').strip()
        guardian_phone = request.form.get('guardian_phone', '').strip()
        branch = request.form.get('branch', '').strip()
        semester = request.form.get('semester', 1)
        gender = request.form.get('gender', 'Male')

        # Validation
        if not username or not full_name or not email or not password:
            flash("Please fill in all required fields marked with *.", "danger")
            return render_template('register.html', form=request.form)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', form=request.form)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', form=request.form)

        # Check existing roll number or email
        existing_user = query_db("SELECT id FROM users WHERE username = ? OR email = ?", (username, email), one=True)
        if existing_user:
            flash("A student account with this Roll Number or Email already exists.", "warning")
            return render_template('register.html', form=request.form)

        # Create new student account
        pw_hash = generate_password_hash(password)
        modify_db("""
            INSERT INTO users (username, full_name, email, password_hash, role, phone, guardian_name, guardian_phone, branch, semester, gender)
            VALUES (?, ?, ?, ?, 'student', ?, ?, ?, ?, ?, ?)
        """, (username, full_name, email, pw_hash, phone, guardian_name, guardian_phone, branch, semester, gender))

        flash("Registration successful! You can now log in with your credentials.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Clear session and log out."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('login'))


# -------------------------------------------------------------
# Notices Routes (Public / Common)
# -------------------------------------------------------------
@app.route('/notices')
def notices():
    """Notice board with category filter and search."""
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()

    sql = """
        SELECT n.*, u.full_name as author_name
        FROM notices n
        JOIN users u ON n.created_by = u.id
        WHERE 1=1
    """
    params = []

    if category and category != 'All':
        sql += " AND n.category = ?"
        params.append(category)

    if search:
        sql += " AND (n.title LIKE ? OR n.content LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard])

    sql += " ORDER BY n.is_pinned DESC, n.created_at DESC"
    notices_list = query_db(sql, params)

    categories = ['All', 'Urgent', 'General', 'Mess', 'Event', 'Maintenance', 'Rules']
    return render_template('notices.html', notices=notices_list, categories=categories,
                           selected_category=category or 'All', search=search)


# -------------------------------------------------------------
# Mess Menu Routes (Public / Common)
# -------------------------------------------------------------
@app.route('/mess-menu')
def mess_menu():
    """Weekly mess menu view with tabbed days."""
    selected_day = request.args.get('day')
    if not selected_day:
        selected_day = datetime.datetime.now().strftime('%A')

    meals = query_db("""
        SELECT * FROM mess_menu
        WHERE day_of_week = ?
        ORDER BY 
            CASE meal_type 
                WHEN 'Breakfast' THEN 1 
                WHEN 'Lunch' THEN 2 
                WHEN 'Snacks' THEN 3 
                WHEN 'Dinner' THEN 4 
            END
    """, (selected_day,))

    return render_template('mess_menu.html', meals=meals, selected_day=selected_day)


# -------------------------------------------------------------
# Student Portal Routes
# -------------------------------------------------------------
@app.route('/student/dashboard')
@student_required
def student_dashboard():
    """Personalized dashboard for logged-in students."""
    user_id = session['user_id']
    
    # Room allotment details
    allotment = query_db("""
        SELECT ra.*, r.room_number, r.block, r.floor, r.room_type, r.monthly_rent, r.description as room_desc
        FROM room_allotments ra
        JOIN rooms r ON ra.room_id = r.id
        WHERE ra.user_id = ? AND ra.status = 'Active'
    """, (user_id,), one=True)
    
    roommates = []
    if allotment:
        roommates = query_db("""
            SELECT u.full_name, u.username, u.branch, u.phone, ra.bed_number
            FROM room_allotments ra
            JOIN users u ON ra.user_id = u.id
            WHERE ra.room_id = ? AND ra.status = 'Active' AND ra.user_id != ?
        """, (allotment['room_id'], user_id))

    # Today's meals
    today = datetime.datetime.now().strftime('%A')
    today_meals = query_db("""
        SELECT * FROM mess_menu 
        WHERE day_of_week = ?
        ORDER BY 
            CASE meal_type 
                WHEN 'Breakfast' THEN 1 
                WHEN 'Lunch' THEN 2 
                WHEN 'Snacks' THEN 3 
                WHEN 'Dinner' THEN 4 
            END
    """, (today,))

    # Student's active complaints
    recent_complaints = query_db("""
        SELECT * FROM complaints
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 4
    """, (user_id,))

    # Student's active outpass requests
    recent_outpasses = query_db("""
        SELECT * FROM outpasses
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 3
    """, (user_id,))

    # Recent pinned notices
    pinned_notices = query_db("""
        SELECT * FROM notices
        ORDER BY is_pinned DESC, created_at DESC
        LIMIT 3
    """)

    return render_template('dashboard_student.html',
                           allotment=allotment,
                           roommates=roommates,
                           today_meals=today_meals,
                           today=today,
                           recent_complaints=recent_complaints,
                           recent_outpasses=recent_outpasses,
                           pinned_notices=pinned_notices)


@app.route('/student/complaints', methods=['GET', 'POST'])
@student_required
def student_complaints():
    """List of complaints filed by the student + form to lodge a new complaint."""
    user_id = session['user_id']
    
    # Fetch student's room number for auto-fill
    user_room = query_db("""
        SELECT r.room_number 
        FROM room_allotments ra
        JOIN rooms r ON ra.room_id = r.id
        WHERE ra.user_id = ? AND ra.status = 'Active'
    """, (user_id,), one=True)

    default_room = user_room['room_number'] if user_room else ''

    if request.method == 'POST':
        category = request.form.get('category', 'Other')
        room_number = request.form.get('room_number', default_room).strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Medium')

        if not title or not description or not category:
            flash("Please provide complaint category, title, and detailed description.", "danger")
        else:
            modify_db("""
                INSERT INTO complaints (user_id, room_number, category, title, description, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending')
            """, (user_id, room_number, category, title, description, priority))
            flash("Your maintenance complaint has been registered. Staff will inspect shortly.", "success")
            return redirect(url_for('student_complaints'))

    complaints_list = query_db("""
        SELECT * FROM complaints
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    return render_template('complaints.html', complaints=complaints_list, default_room=default_room)


@app.route('/student/outpass', methods=['GET', 'POST'])
@student_required
def student_outpass():
    """Digital leave/outpass request module for students."""
    user_id = session['user_id']
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)

    if request.method == 'POST':
        departure_time = request.form.get('departure_time', '').strip()
        expected_return = request.form.get('expected_return', '').strip()
        reason = request.form.get('reason', '').strip()
        destination = request.form.get('destination', '').strip()
        emergency_contact = request.form.get('emergency_contact', user['guardian_phone'] or user['phone']).strip()

        if not departure_time or not expected_return or not reason or not destination:
            flash("All leave details are required to submit an outpass request.", "danger")
        else:
            modify_db("""
                INSERT INTO outpasses (user_id, departure_time, expected_return, reason, destination, emergency_contact, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending')
            """, (user_id, departure_time, expected_return, reason, destination, emergency_contact))
            flash("Outpass application submitted successfully. Warden will review your request.", "success")
            return redirect(url_for('student_outpass'))

    outpasses_list = query_db("""
        SELECT * FROM outpasses
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    return render_template('outpass.html', outpasses=outpasses_list, user=user)


@app.route('/student/outpass/<int:outpass_id>/pass')
@login_required
def view_gate_pass(outpass_id):
    """View / Print official digital gate pass for security checkpoint."""
    user_id = session['user_id']
    role = session.get('role')

    # Security check: Only the student themselves or an admin can view the pass
    outpass = query_db("""
        SELECT o.*, u.full_name, u.username as roll_number, u.branch, u.phone, u.guardian_phone,
               r.room_number, r.block,
               w.full_name as reviewer_name
        FROM outpasses o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN room_allotments ra ON ra.user_id = u.id AND ra.status = 'Active'
        LEFT JOIN rooms r ON ra.room_id = r.id
        LEFT JOIN users w ON o.reviewed_by = w.id
        WHERE o.id = ?
    """, (outpass_id,), one=True)

    if not outpass:
        abort(404)

    if role != 'admin' and outpass['user_id'] != user_id:
        abort(403)

    return render_template('gate_pass.html', outpass=outpass)


@app.route('/student/room')
@student_required
def student_room():
    """View allocated room details, specifications, and roommate contacts."""
    user_id = session['user_id']
    
    allotment = query_db("""
        SELECT ra.*, r.room_number, r.block, r.floor, r.capacity, r.room_type, r.monthly_rent, r.description, r.status as room_status
        FROM room_allotments ra
        JOIN rooms r ON ra.room_id = r.id
        WHERE ra.user_id = ? AND ra.status = 'Active'
    """, (user_id,), one=True)

    roommates = []
    if allotment:
        roommates = query_db("""
            SELECT u.full_name, u.username, u.email, u.phone, u.branch, u.semester, ra.bed_number, ra.allotted_date
            FROM room_allotments ra
            JOIN users u ON ra.user_id = u.id
            WHERE ra.room_id = ? AND ra.status = 'Active' AND ra.user_id != ?
        """, (allotment['room_id'], user_id))

    return render_template('rooms.html', allotment=allotment, roommates=roommates)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management (student or admin)."""
    user_id = session['user_id']
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        guardian_name = request.form.get('guardian_name', '').strip()
        guardian_phone = request.form.get('guardian_phone', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if new_password:
            if new_password != confirm_password:
                flash("New passwords do not match.", "danger")
                return redirect(url_for('profile'))
            if len(new_password) < 6:
                flash("Password must be at least 6 characters.", "danger")
                return redirect(url_for('profile'))
            
            modify_db("""
                UPDATE users
                SET phone = ?, guardian_name = ?, guardian_phone = ?, password_hash = ?
                WHERE id = ?
            """, (phone, guardian_name, guardian_phone, generate_password_hash(new_password), user_id))
            flash("Profile and password updated successfully.", "success")
        else:
            modify_db("""
                UPDATE users
                SET phone = ?, guardian_name = ?, guardian_phone = ?
                WHERE id = ?
            """, (phone, guardian_name, guardian_phone, user_id))
            flash("Profile information updated successfully.", "success")

        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


# -------------------------------------------------------------
# Administrator Portal Routes
# -------------------------------------------------------------
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Administrator executive dashboard with live metrics and pending approvals."""
    # Summary Metrics
    total_students = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student'", one=True)['c']
    total_rooms = query_db("SELECT COUNT(*) as c FROM rooms", one=True)['c']
    occupied_beds = query_db("SELECT COUNT(*) as c FROM room_allotments WHERE status = 'Active'", one=True)['c']
    total_capacity = query_db("SELECT COALESCE(SUM(capacity), 0) as s FROM rooms", one=True)['s']
    occupancy_pct = round((occupied_beds / total_capacity * 100), 1) if total_capacity else 0

    pending_complaints = query_db("SELECT COUNT(*) as c FROM complaints WHERE status = 'Pending'", one=True)['c']
    pending_outpasses = query_db("SELECT COUNT(*) as c FROM outpasses WHERE status = 'Pending'", one=True)['c']
    total_notices = query_db("SELECT COUNT(*) as c FROM notices", one=True)['c']

    # Urgent / Pending items
    recent_complaints = query_db("""
        SELECT c.*, u.full_name as student_name, u.username as roll_number
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        ORDER BY 
            CASE c.priority 
                WHEN 'Urgent' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                ELSE 4 
            END,
            c.created_at DESC
        LIMIT 5
    """)

    recent_outpasses = query_db("""
        SELECT o.*, u.full_name as student_name, u.username as roll_number, r.room_number
        FROM outpasses o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN room_allotments ra ON ra.user_id = u.id AND ra.status = 'Active'
        LEFT JOIN rooms r ON ra.room_id = r.id
        WHERE o.status = 'Pending'
        ORDER BY o.created_at ASC
        LIMIT 5
    """)

    stats = {
        'total_students': total_students,
        'total_rooms': total_rooms,
        'occupied_beds': occupied_beds,
        'total_capacity': total_capacity,
        'occupancy_pct': occupancy_pct,
        'pending_complaints': pending_complaints,
        'pending_outpasses': pending_outpasses,
        'total_notices': total_notices
    }

    return render_template('dashboard_admin.html',
                           stats=stats,
                           recent_complaints=recent_complaints,
                           recent_outpasses=recent_outpasses)


# --- Admin Notice Management ---
@app.route('/admin/notices')
@admin_required
def admin_notices():
    """Admin notice management table with filter & actions."""
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()

    sql = """
        SELECT n.*, u.full_name as author_name
        FROM notices n
        JOIN users u ON n.created_by = u.id
        WHERE 1=1
    """
    params = []
    if category and category != 'All':
        sql += " AND n.category = ?"
        params.append(category)
    if search:
        sql += " AND (n.title LIKE ? OR n.content LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard])

    sql += " ORDER BY n.is_pinned DESC, n.created_at DESC"
    notices_list = query_db(sql, params)

    return render_template('admin_notices.html', notices=notices_list, selected_category=category or 'All', search=search)


@app.route('/admin/notices/new', methods=['GET', 'POST'])
@admin_required
def admin_new_notice():
    """Publish a new notice."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'General')
        content = request.form.get('content', '').strip()
        is_pinned = 1 if request.form.get('is_pinned') else 0

        if not title or not content:
            flash("Notice title and content cannot be blank.", "danger")
        else:
            modify_db("""
                INSERT INTO notices (title, category, content, is_pinned, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (title, category, content, is_pinned, session['user_id']))
            flash("Notice published successfully to the student board.", "success")
            return redirect(url_for('admin_notices'))

    return render_template('admin_notice_form.html', notice=None)


@app.route('/admin/notices/<int:notice_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_notice(notice_id):
    """Edit existing notice."""
    notice = query_db("SELECT * FROM notices WHERE id = ?", (notice_id,), one=True)
    if not notice:
        abort(404)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'General')
        content = request.form.get('content', '').strip()
        is_pinned = 1 if request.form.get('is_pinned') else 0

        if not title or not content:
            flash("Notice title and content cannot be blank.", "danger")
        else:
            modify_db("""
                UPDATE notices 
                SET title = ?, category = ?, content = ?, is_pinned = ?
                WHERE id = ?
            """, (title, category, content, is_pinned, notice_id))
            flash("Notice updated successfully.", "success")
            return redirect(url_for('admin_notices'))

    return render_template('admin_notice_form.html', notice=notice)


@app.route('/admin/notices/<int:notice_id>/delete', methods=['POST'])
@admin_required
def admin_delete_notice(notice_id):
    """Delete a notice."""
    modify_db("DELETE FROM notices WHERE id = ?", (notice_id,))
    flash("Notice deleted successfully.", "info")
    return redirect(url_for('admin_notices'))


# --- Admin Mess Menu Management ---
@app.route('/admin/mess', methods=['GET', 'POST'])
@admin_required
def admin_mess():
    """Admin mess menu schedule editor."""
    selected_day = request.args.get('day', 'Monday')

    if request.method == 'POST':
        day = request.form.get('day_of_week')
        meal_type = request.form.get('meal_type')
        items = request.form.get('items', '').strip()
        timings = request.form.get('timings', '').strip()
        special_note = request.form.get('special_note', '').strip()

        if not day or not meal_type or not items:
            flash("Please specify day, meal type, and menu items.", "danger")
        else:
            modify_db("""
                INSERT OR REPLACE INTO mess_menu (day_of_week, meal_type, items, timings, special_note, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (day, meal_type, items, timings, special_note))
            flash(f"Updated {meal_type} menu for {day}.", "success")
            return redirect(url_for('admin_mess', day=day))

    meals = query_db("""
        SELECT * FROM mess_menu 
        WHERE day_of_week = ?
        ORDER BY 
            CASE meal_type 
                WHEN 'Breakfast' THEN 1 
                WHEN 'Lunch' THEN 2 
                WHEN 'Snacks' THEN 3 
                WHEN 'Dinner' THEN 4 
            END
    """, (selected_day,))

    return render_template('admin_mess.html', meals=meals, selected_day=selected_day)


# --- Admin Complaints Tracking ---
@app.route('/admin/complaints')
@admin_required
def admin_complaints():
    """Complaints management workbench."""
    status_filter = request.args.get('status', 'All')
    category_filter = request.args.get('category', 'All')

    sql = """
        SELECT c.*, u.full_name as student_name, u.username as roll_number, u.phone as student_phone
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        WHERE 1=1
    """
    params = []

    if status_filter != 'All':
        sql += " AND c.status = ?"
        params.append(status_filter)

    if category_filter != 'All':
        sql += " AND c.category = ?"
        params.append(category_filter)

    sql += """
        ORDER BY 
            CASE c.status
                WHEN 'Pending' THEN 1
                WHEN 'In Progress' THEN 2
                WHEN 'Resolved' THEN 3
                ELSE 4
            END,
            c.created_at DESC
    """
    complaints_list = query_db(sql, params)

    return render_template('admin_complaints.html',
                           complaints=complaints_list,
                           selected_status=status_filter,
                           selected_category=category_filter)


@app.route('/admin/complaints/<int:complaint_id>/update', methods=['POST'])
@admin_required
def admin_update_complaint(complaint_id):
    """Update complaint status and append maintenance notes."""
    status = request.form.get('status')
    remarks = request.form.get('admin_remarks', '').strip()

    resolved_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'Resolved' else None

    modify_db("""
        UPDATE complaints
        SET status = ?, admin_remarks = ?, resolved_at = COALESCE(?, resolved_at)
        WHERE id = ?
    """, (status, remarks, resolved_at, complaint_id))

    flash(f"Complaint #{complaint_id} updated to '{status}'.", "success")
    return redirect(url_for('admin_complaints'))


# --- Admin Outpass / Leave Workflow ---
@app.route('/admin/outpass')
@admin_required
def admin_outpass():
    """Leave & Outpass management console."""
    status_filter = request.args.get('status', 'Pending')

    sql = """
        SELECT o.*, u.full_name as student_name, u.username as roll_number, u.phone as student_phone,
               u.guardian_name, u.guardian_phone,
               r.room_number, r.block,
               w.full_name as reviewer_name
        FROM outpasses o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN room_allotments ra ON ra.user_id = u.id AND ra.status = 'Active'
        LEFT JOIN rooms r ON ra.room_id = r.id
        LEFT JOIN users w ON o.reviewed_by = w.id
        WHERE 1=1
    """
    params = []
    if status_filter != 'All':
        sql += " AND o.status = ?"
        params.append(status_filter)

    sql += " ORDER BY o.created_at DESC"
    outpasses_list = query_db(sql, params)

    return render_template('admin_outpass.html', outpasses=outpasses_list, selected_status=status_filter)


@app.route('/admin/outpass/<int:outpass_id>/review', methods=['POST'])
@admin_required
def admin_review_outpass(outpass_id):
    """Approve or reject outpass application."""
    decision = request.form.get('decision')  # 'Approved' or 'Rejected'
    remarks = request.form.get('admin_remarks', '').strip()

    if decision not in ('Approved', 'Rejected'):
        flash("Invalid decision.", "danger")
        return redirect(url_for('admin_outpass'))

    modify_db("""
        UPDATE outpasses
        SET status = ?, admin_remarks = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (decision, remarks, session['user_id'], outpass_id))

    flash(f"Outpass #{outpass_id} has been marked as '{decision}'.", "success" if decision == 'Approved' else "warning")
    return redirect(url_for('admin_outpass'))


@app.route('/admin/outpass/<int:outpass_id>/mark-returned', methods=['POST'])
@admin_required
def admin_mark_returned(outpass_id):
    """Mark student as returned back to hostel campus."""
    modify_db("""
        UPDATE outpasses
        SET status = 'Returned', actual_return = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (outpass_id,))

    flash(f"Student return recorded for Outpass #{outpass_id}.", "info")
    return redirect(url_for('admin_outpass', status='All'))


# --- Admin Rooms & Allotment Management ---
@app.route('/admin/rooms', methods=['GET', 'POST'])
@admin_required
def admin_rooms():
    """Room inventory management, adding rooms, and room allotment."""
    if request.method == 'POST' and request.form.get('action') == 'add_room':
        room_number = request.form.get('room_number', '').strip()
        block = request.form.get('block', '').strip()
        floor = request.form.get('floor', 1, type=int)
        capacity = request.form.get('capacity', 2, type=int)
        room_type = request.form.get('room_type', 'Non-AC')
        monthly_rent = request.form.get('monthly_rent', 4500.0, type=float)
        description = request.form.get('description', '').strip()

        if not room_number or not block:
            flash("Room number and block are mandatory.", "danger")
        else:
            try:
                modify_db("""
                    INSERT INTO rooms (room_number, block, floor, capacity, room_type, monthly_rent, status, description)
                    VALUES (?, ?, ?, ?, ?, ?, 'Available', ?)
                """, (room_number, block, floor, capacity, room_type, monthly_rent, description))
                flash(f"Room {room_number} added to hostel inventory.", "success")
            except Exception as e:
                flash(f"Error adding room (room number may already exist): {e}", "danger")
        return redirect(url_for('admin_rooms'))

    block_filter = request.args.get('block', 'All')

    sql = """
        SELECT r.*,
               COUNT(ra.id) as current_occupancy
        FROM rooms r
        LEFT JOIN room_allotments ra ON r.id = ra.room_id AND ra.status = 'Active'
        WHERE 1=1
    """
    params = []
    if block_filter != 'All':
        sql += " AND r.block = ?"
        params.append(block_filter)

    sql += " GROUP BY r.id ORDER BY r.block, r.floor, r.room_number"
    rooms_list = query_db(sql, params)

    # Fetch unallocated students for quick allotment dropdown
    unallocated_students = query_db("""
        SELECT u.id, u.username, u.full_name, u.branch, u.gender
        FROM users u
        WHERE u.role = 'student'
          AND u.id NOT IN (SELECT user_id FROM room_allotments WHERE status = 'Active')
        ORDER BY u.full_name
    """)

    # Fetch all active allotments for occupant listing
    allotments = query_db("""
        SELECT ra.id as allotment_id, ra.bed_number, ra.allotted_date, ra.room_id,
               u.id as student_id, u.full_name, u.username as roll_number, u.phone
        FROM room_allotments ra
        JOIN users u ON ra.user_id = u.id
        WHERE ra.status = 'Active'
    """)

    # Group occupants by room_id
    room_occupants = {}
    for a in allotments:
        room_occupants.setdefault(a['room_id'], []).append(a)

    blocks = query_db("SELECT DISTINCT block FROM rooms ORDER BY block")

    return render_template('admin_rooms.html',
                           rooms=rooms_list,
                           room_occupants=room_occupants,
                           unallocated_students=unallocated_students,
                           blocks=[b['block'] for b in blocks],
                           selected_block=block_filter)


@app.route('/admin/rooms/allot', methods=['POST'])
@admin_required
def admin_allot_room():
    """Allot a student to a room bed."""
    student_id = request.form.get('student_id', type=int)
    room_id = request.form.get('room_id', type=int)
    bed_number = request.form.get('bed_number', 1, type=int)

    if not student_id or not room_id:
        flash("Please select both a student and a target room.", "danger")
        return redirect(url_for('admin_rooms'))

    # Check room capacity
    room = query_db("SELECT * FROM rooms WHERE id = ?", (room_id,), one=True)
    current_count = query_db("""
        SELECT COUNT(*) as c FROM room_allotments 
        WHERE room_id = ? AND status = 'Active'
    """, (room_id,), one=True)['c']

    if current_count >= room['capacity']:
        flash(f"Room {room['room_number']} is already at full capacity ({room['capacity']} beds).", "danger")
        return redirect(url_for('admin_rooms'))

    # Deactivate any previous active allotment
    modify_db("UPDATE room_allotments SET status = 'Vacated' WHERE user_id = ?", (student_id,))

    # Insert new allotment
    modify_db("""
        INSERT INTO room_allotments (user_id, room_id, bed_number, status)
        VALUES (?, ?, ?, 'Active')
    """, (student_id, room_id, bed_number))

    # Update room status if full
    if current_count + 1 >= room['capacity']:
        modify_db("UPDATE rooms SET status = 'Occupied' WHERE id = ?", (room_id,))

    flash(f"Student successfully allotted to Room {room['room_number']} (Bed #{bed_number}).", "success")
    return redirect(url_for('admin_rooms'))


@app.route('/admin/rooms/deallot/<int:allotment_id>', methods=['POST'])
@admin_required
def admin_deallot_room(allotment_id):
    """Deallocate student from their room."""
    allotment = query_db("SELECT * FROM room_allotments WHERE id = ?", (allotment_id,), one=True)
    if allotment:
        modify_db("UPDATE room_allotments SET status = 'Vacated' WHERE id = ?", (allotment_id,))
        modify_db("UPDATE rooms SET status = 'Available' WHERE id = ?", (allotment['room_id'],))
        flash("Student deallocated and bed freed.", "info")
    return redirect(url_for('admin_rooms'))


# --- Admin Student Directory ---
@app.route('/admin/students')
@admin_required
def admin_students():
    """Student roster and directory."""
    search = request.args.get('search', '').strip()

    sql = """
        SELECT u.*,
               r.room_number, r.block, ra.bed_number, ra.id as allotment_id
        FROM users u
        LEFT JOIN room_allotments ra ON u.id = ra.user_id AND ra.status = 'Active'
        LEFT JOIN rooms r ON ra.room_id = r.id
        WHERE u.role = 'student'
    """
    params = []
    if search:
        sql += " AND (u.full_name LIKE ? OR u.username LIKE ? OR u.branch LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard])

    sql += " ORDER BY u.username ASC"
    students_list = query_db(sql, params)

    return render_template('admin_students.html', students=students_list, search=search)


# -------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Ensure database is initialized
    if not os.path.exists('hostel.db'):
        import seed_data
        seed_data.seed()
    
    # Run development server
    port = int(os.environ.get('PORT', 5001))
    print(f"Hostel Management System running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
