from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3

auth_bp = Blueprint('auth', __name__)

def get_db_connection():
    conn = sqlite3.connect('library1.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login', next=request.url))
            
            if session.get('role') not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    
    if user_id is None:
        g.user = None
    else:
        conn = get_db_connection()
        g.user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required!', 'error')
            return redirect(url_for('auth.login'))
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user is None:
            flash('Invalid username or password!', 'error')
            return redirect(url_for('auth.login'))
        
        if not check_password_hash(user['password'], password):
            flash('Invalid username or password!', 'error')
            return redirect(url_for('auth.login'))
        
        # Store user info in session
        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        next_url = request.args.get('next')
        if next_url:
            return redirect(next_url)
        
        flash(f'Welcome, {username}!', 'success')
        return redirect(url_for('index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        
        if not username or not password or not email or not name:
            flash('All fields are required!', 'error')
            return redirect(url_for('auth.register'))
        
        conn = get_db_connection()
        
        # Check if username exists
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            conn.close()
            flash('Username already exists!', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if email exists
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            conn.close()
            flash('Email already exists!', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user
        hashed_password = generate_password_hash(password)
        
        try:
            # Insert user
            cursor = conn.execute('''
            INSERT INTO users (username, password, email, role)
            VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, email, 'member'))
            
            user_id = cursor.lastrowid
            
            # Insert member
            conn.execute('''
            INSERT INTO members (name, email, user_id)
            VALUES (?, ?, ?)
            ''', (name, email, user_id))
            
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('An error occurred. Please try again.', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # If user is a member, get member details
    member = None
    if user['role'] == 'member':
        member = conn.execute('SELECT * FROM members WHERE user_id = ?', (user['id'],)).fetchone()
    
    # Get user's reservations
    reservations = conn.execute('''
        SELECT r.*, b.title AS book_title
        FROM reservations r
        JOIN books b ON r.book_id = b.id
        WHERE r.user_id = ?
        ORDER BY r.reservation_date DESC
    ''', (user['id'],)).fetchall()
    
    conn.close()
    
    return render_template('auth/profile.html', user=user, member=member, reservations=reservations)