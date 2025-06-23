from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import sqlite3
import os
import io
import hashlib
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('HFD_Data.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Authentication helper functions
def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    """Check if password matches hash"""
    return hash_password(password) == hashed

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        user = conn.execute('SELECT isAdmin FROM users_list WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        
        if not user or not user['isAdmin']:
            flash('Admin access required.', 'error')
            return redirect(url_for('homepage'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_context():
    """Get current user context for templates"""
    if 'user_id' in session:
        return {
            'logged_in': True,  # Add this missing key
            'username': session['username'],
            'is_admin': session['is_admin'],
            'address': session.get('address', ''),
            'user_id': session['user_id']  # Add this for consistency
        }
    return {'logged_in': False, 'is_admin': False, 'username': '', 'address': '', 'user_id': None}

def init_database():
    """Initialize the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
   
    # Create restaurants table with id field
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rest_name TEXT NOT NULL,
        rest_score FLOAT,
        delivery_fee FLOAT,
        details TEXT,
        description TEXT,
        cover_image BLOB
    )
    ''')
   
    # Check if we need to add sample data
    existing = cursor.execute('SELECT COUNT(*) FROM restaurants').fetchone()[0]
    if existing == 0:
        restaurants = [
            ('Subway', 4.3, 2.5, 'fast_food', 'Subway primarily sells sandwiches and fresh food'),
            ('Tank', 4.6, 2.0, 'fast_food', 'Tank primarily sells energy drinks and beverages'),
            ('One Sushi', 4.5, 2.5, 'sushi_bar', 'One Sushi primarily sells fresh sushi and Japanese cuisine'),
            ('Noodle Kim', 4.3, 3.5, 'fast_food', 'Noodle Kim mainly sells noodle dishes and Asian cuisine')
        ]
        cursor.executemany('''
            INSERT INTO restaurants (rest_name, rest_score, delivery_fee, details, description)
            VALUES (?, ?, ?, ?, ?)
        ''', restaurants)
        print("Added sample data")
   
    conn.commit()
    conn.close()

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        address = request.form['address']  # Address entered during login
       
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users_list WHERE username = ?', (username,)).fetchone()
       
        if user and check_password(password, user['password']):
            # Update user's address in database
            conn.execute('UPDATE users_list SET address = ? WHERE id = ?', (address, user['id']))
            conn.commit()
           
            # Set session variables - make sure all required keys are set
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['isAdmin'])  # Use correct column name
            session['address'] = address
           
            # Debug output
            print(f"=== LOGIN SUCCESS ===")
            print(f"User: {username}")
            print(f"Admin status: {session['is_admin']}")
            print(f"Session data: {dict(session)}")
            print("====================")
           
            conn.close()
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('homepage'))
        else:
            flash('Invalid username or password.', 'error')
            conn.close()
   
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        address = request.form['address']
        
        # Handle checkbox values for admin (only present in form if checked)
        isAdmin = 1 if 'admin_confirmation' in request.form else 0
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        conn = get_db_connection()
        
        # Check if username or email already exists
        existing_user = conn.execute(
            'SELECT id FROM users_list WHERE username = ? OR email = ?', 
            (username, email)
        ).fetchone()
        
        if existing_user:
            flash('Username or email already exists.', 'error')
            conn.close()
            return render_template('auth/register.html')
        
        #Code to confirm weather or not admin is valid

        # Hash password and insert user
        #If the current user is not an admin user
        if isAdmin == 0:
            hashed_password = hash_password(password)
            cursor = conn.execute('''
                INSERT INTO users_list (username, password, email, address, isAdmin)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, hashed_password, email, address, isAdmin))
        
            conn.commit()
            conn.close()
        
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        elif isAdmin == 1:
            adminKey = request.form['admin_key']
            if adminKey == 'W@T3RF00d#34454':
                hashed_password = hash_password(password)
                cursor = conn.execute('''
                    INSERT INTO users_list (username, password, email, address, isAdmin)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, hashed_password, email, address, isAdmin))
        
                conn.commit()
                conn.close()
        
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('incorrect admin key.', 'error')
                return render_template('auth/register.html')

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'success')
    return redirect(url_for('homepage'))

@app.route('/view_users')
@admin_required
def view_users():
    """Admin-only route to view all users"""
    try:
        conn = get_db_connection()
        # Fixed query - use the correct column names from your database
        all_users = conn.execute('''
            SELECT id, username, email, address, isAdmin
            FROM users_list
            ORDER BY isAdmin DESC, username ASC
        ''').fetchall()
        conn.close()
       
        print(f"Found {len(all_users)} users")
       
        # Add user context
        context = get_user_context()
        context['users_list'] = all_users
        context['current_user_id'] = session.get('user_id')
       
        # Use the correct template name
        return render_template('auth/See_Users.html', **context)
       
    except Exception as e:
        print(f"Error in view users: {e}")
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('homepage'))
 
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Admin-only route to delete a user"""
    # Prevent self-deletion
    if user_id == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('view_users'))
   
    try:
        conn = get_db_connection()
       
        # Check if user exists and get their info - use correct column name
        user_to_delete = conn.execute(
            'SELECT username, isAdmin FROM users_list WHERE id = ?',
            (user_id,)
        ).fetchone()
       
        if not user_to_delete:
            flash('User not found.', 'error')
            conn.close()
            return redirect(url_for('view_users'))
       
        # Check if this is the last admin - use correct column name
        if user_to_delete['isAdmin']:
            admin_count = conn.execute(
                'SELECT COUNT(*) as count FROM users_list WHERE isAdmin = 1'
            ).fetchone()['count']
           
            if admin_count <= 1:
                flash('Cannot delete the last admin user.', 'error')
                conn.close()
                return redirect(url_for('view_users'))
       
        # Delete the user
        conn.execute('DELETE FROM users_list WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
       
        flash(f'User "{user_to_delete["username"]}" has been successfully deleted.', 'success')
       
    except Exception as e:
        print(f"Error deleting user: {e}")
        flash(f'Error deleting user: {str(e)}', 'error')
   
    return redirect(url_for('view_users'))
 
# Debug route to check your database structure
@app.route('/debug_users')
def debug_users():
    """Debug route to see actual database content"""
    try:
        conn = get_db_connection()
       
        # Check table structure
        table_info = conn.execute("PRAGMA table_info(users_list)").fetchall()
       
        # Get all users
        users = conn.execute("SELECT * FROM users_list").fetchall()
       
        conn.close()
       
        # Format output
        columns = [col['name'] for col in table_info]
        user_data = []
        for user in users:
            user_dict = dict(user)
            user_data.append(user_dict)
       
        return f"""
        <h1>Database Debug Info</h1>
        <h2>Table Columns:</h2>
        <p>{columns}</p>
       
        <h2>All Users:</h2>
        <ul>
        {''.join([f'<li>ID: {user["id"]}, Username: {user["username"]}, isAdmin: {user.get("isAdmin", "N/A")}</li>' for user in user_data])}
        </ul>
       
        <h2>Current Session:</h2>
        <p>{dict(session)}</p>
       
        <p><a href="{url_for('homepage')}">Back to Home</a></p>
        """
       
    except Exception as e:
        return f"<h1>Error:</h1><p>{str(e)}</p>"


# Test route to check if Flask is working
@app.route('/test')
def test():
    return "<h1>Flask is working!</h1><p>If you see this, the Flask app is running correctly.</p>"

@app.route('/')
def homepage():
    try:
        conn = get_db_connection()
        restaurants = conn.execute('SELECT * FROM restaurants ORDER BY id').fetchall()
        conn.close()
        
        # Add user context
        context = get_user_context()
        context['restaurants'] = restaurants
        
        print(f"Found {len(restaurants)} restaurants")
        return render_template('index.html', **context)
    except Exception as e:
        print(f"Error in homepage: {e}")
        return f"<h1>Error:</h1><p>{str(e)}</p><p><a href='/test'>Test Flask</a></p>"

@app.route('/add_restaurant', methods=['GET', 'POST'])
@admin_required  # Only admins can add restaurants
def add_restaurant():
    if request.method == 'POST':
        try:
            rest_name = request.form['rest_name']
            rest_score = float(request.form['rest_score'])
            delivery_fee = float(request.form['delivery_fee'])
            details = request.form['details']
            description = request.form['description']
           
            # Handle image upload (store as-is without processing)
            cover_image_data = None
            if 'cover_image' in request.files:
                file = request.files['cover_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    cover_image_data = file.read()
           
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO restaurants (rest_name, rest_score, delivery_fee, details, description, cover_image)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (rest_name, rest_score, delivery_fee, details, description, cover_image_data))
            conn.commit()
            conn.close()
           
            flash('Restaurant added successfully!', 'success')
            return redirect(url_for('homepage'))
        except Exception as e:
            print(f"Error adding restaurant: {e}")
            flash(f'Error: {str(e)}', 'error')
   
    context = get_user_context()
    return render_template('add_restaurant.html', **context)

@app.route('/edit_restaurant/<int:restaurant_id>', methods=['GET', 'POST'])
@admin_required  # Only admins can edit restaurants
def edit_restaurant(restaurant_id):
    conn = get_db_connection()
   
    if request.method == 'POST':
        try:
            rest_name = request.form['rest_name']
            rest_score = float(request.form['rest_score'])
            delivery_fee = float(request.form['delivery_fee'])
            details = request.form['details']
            description = request.form['description']
           
            # Handle image upload
            cover_image_data = None
            update_image = False
           
            if 'cover_image' in request.files:
                file = request.files['cover_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    cover_image_data = file.read()
                    update_image = True
           
            # Update restaurant data
            if update_image:
                conn.execute('''
                    UPDATE restaurants
                    SET rest_name=?, rest_score=?, delivery_fee=?, details=?, description=?, cover_image=?
                    WHERE id=?
                ''', (rest_name, rest_score, delivery_fee, details, description, cover_image_data, restaurant_id))
            else:
                conn.execute('''
                    UPDATE restaurants
                    SET rest_name=?, rest_score=?, delivery_fee=?, details=?, description=?
                    WHERE id=?
                ''', (rest_name, rest_score, delivery_fee, details, description, restaurant_id))
           
            conn.commit()
            conn.close()
           
            flash('Restaurant updated successfully!', 'success')
            return redirect(url_for('homepage'))
        except Exception as e:
            print(f"Error updating restaurant: {e}")
            flash(f'Error: {str(e)}', 'error')
   
    # GET request - show the form with current data
    restaurant = conn.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
    conn.close()
   
    if not restaurant:
        flash('Restaurant not found!', 'error')
        return redirect(url_for('homepage'))
   
    context = get_user_context()
    context['restaurant'] = restaurant
    return render_template('edit_restaurant.html', **context)

@app.route('/delete_restaurant/<int:restaurant_id>', methods=['POST'])
@admin_required  # Only admins can delete restaurants
def delete_restaurant(restaurant_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM restaurants WHERE id = ?', (restaurant_id,))
        conn.execute('DELETE FROM menu_items WHERE restaurant_id = ?', (restaurant_id,))
        conn.commit()
        conn.close()
       
        flash('Restaurant deleted successfully!', 'success')
    except Exception as e:
        print(f"Error deleting restaurant: {e}")
        flash(f'Error: {str(e)}', 'error')
   
    return redirect(url_for('homepage'))

@app.route('/restaurant_image/<int:restaurant_id>')
def get_restaurant_image(restaurant_id):
    try:
        conn = get_db_connection()
        restaurant = conn.execute('SELECT cover_image FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
        conn.close()
       
        if restaurant and restaurant['cover_image']:
            return send_file(
                io.BytesIO(restaurant['cover_image']),
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=f'restaurant_{restaurant_id}.jpg'
            )
        else:
            return '', 404
    except Exception as e:
        print(f"Error getting image: {e}")
        return '', 404

@app.route('/upload_bulk_images')
@admin_required  # Only admins can bulk upload
def upload_bulk_images():
    """Route to upload multiple images at once"""
    context = get_user_context()
    return render_template('bulk_upload.html', **context)

@app.route('/upload_bulk_images', methods=['POST'])
@admin_required  # Only admins can bulk upload
def handle_bulk_upload():
    """Handle bulk image upload"""
    try:
        restaurants_data = {
            'subway': 1,
            'tank': 2,
            'one_sushi': 3,
            'noodle_kim': 4
        }
       
        conn = get_db_connection()
       
        for restaurant_name, restaurant_id in restaurants_data.items():
            file_key = f'{restaurant_name}_image'
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename != '' and allowed_file(file.filename):
                    image_data = file.read()
                   
                    conn.execute('''
                        UPDATE restaurants SET cover_image = ? WHERE id = ?
                    ''', (image_data, restaurant_id))
       
        conn.commit()
        conn.close()
       
        flash('Images uploaded successfully!', 'success')
        return redirect(url_for('homepage'))
       
    except Exception as e:
        print(f"Error in bulk upload: {e}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('upload_bulk_images'))

@app.route('/add_rest_image/<int:restaurant_id>', methods=['GET', 'POST'])
def add_restaurant_image(restaurant_id):
    conn = get_db_connection()
   
    if request.method == 'POST':
        try:
            # Handle image upload
            if 'restaurant_image' in request.files:  
                file = request.files['restaurant_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    image_data = file.read()
                   
                    # Update the restaurant with the image
                    conn.execute('''
                        UPDATE restaurants SET cover_image = ? WHERE id = ?
                    ''', (image_data, restaurant_id))
                    conn.commit()
                   
                    flash('Restaurant image uploaded successfully!', 'success')
                    conn.close()
                    return redirect(url_for('homepage'))
               
                else:
                    flash('Please select a valid image file', 'error')
            else:
                flash('No image file selected', 'error')
               
        except Exception as e:
            print(f"Error uploading restaurant image: {e}")
            flash(f'Error: {str(e)}', 'error')
   
    # Get restaurant data to pass to template
    restaurant = conn.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
    conn.close()
   
    if not restaurant:
        flash('Restaurant not found!', 'error')
        return redirect(url_for('homepage'))
 
    context = get_user_context()
    context.update({'restaurant': restaurant, 'restaurant_id': restaurant_id})
    return render_template('Add_rest_image.html', **context)

#Loads the page for each restauraunt
@app.route('/view_restaurant/<int:restaurant_id>')
def view_restaurant(restaurant_id):
    conn = get_db_connection()
    restaurant = conn.execute('''
        SELECT * FROM restaurants WHERE id = ?
    ''', (restaurant_id,)).fetchone()
   
    if not restaurant:
        flash('Restaurant not found!', 'error')
        conn.close()
        return redirect(url_for('homepage'))

    memu_items = conn.execute('SELECT * FROM menu_items WHERE restaurant_id = ? ORDER BY id', (restaurant_id,)).fetchall()
    print(f"Found {len(memu_items)} items")  # Debug print
    conn.close()
    
    # Add user context
    context = get_user_context()
    context.update({'restaurant': restaurant, 'memu_items': memu_items})
    return render_template('view_restaurant/view.html', **context)

#Loads the menu where the user can upload an imagre for the food
@app.route('/add_menu_image/<int:menu_id>', methods=['GET', 'POST'])
@admin_required  # Only admins can edit restaurants
def add_item_image(menu_id):
    conn = get_db_connection()
   
    if request.method == 'POST':
        try:
            # Handle image upload
            if 'menu_image' in request.files:
                file = request.files['menu_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    image_data = file.read()
                   
                    # Update the menu item with the image
                    conn.execute('''
                        UPDATE menu_items SET image_data = ? WHERE id = ?
                    ''', (image_data, menu_id))
                    conn.commit()
                   
                    flash('Menu item image uploaded successfully!', 'success')
                   
                    # Get restaurant_id to redirect back to restaurant page
                    menu_item = conn.execute('SELECT restaurant_id FROM menu_items WHERE id = ?', (menu_id,)).fetchone()
                    conn.close()
                   
                    if menu_item:
                        return redirect(url_for('view_restaurant', restaurant_id=menu_item['restaurant_id']))
                else:
                    flash('Please select a valid image file', 'error')
            else:
                flash('No image file selected', 'error')
               
        except Exception as e:
            print(f"Error uploading menu image: {e}")
            flash(f'Error: {str(e)}', 'error')
   
    # GET request - get menu item details for the form
    menu_item = conn.execute('''
        SELECT mi.*, r.rest_name
        FROM menu_items mi
        JOIN restaurants r ON mi.restaurant_id = r.id
        WHERE mi.id = ?
    ''', (menu_id,)).fetchone()
    conn.close()
   
    if not menu_item:
        flash('Menu item not found!', 'error')
        return redirect(url_for('homepage'))

    context = get_user_context()
    context['menu_item'] = menu_item
    return render_template('view_restaurant/Add_image.html', **context)

# ROUTE to serve menu item images
@app.route('/menu_image/<int:menu_id>')
def get_menu_image(menu_id):
    try:
        conn = get_db_connection()
        menu_item = conn.execute('SELECT image_data FROM menu_items WHERE id = ?', (menu_id,)).fetchone()
        conn.close()
       
        if menu_item and menu_item['image_data']:
            return send_file(
                io.BytesIO(menu_item['image_data']),
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=f'menu_item_{menu_id}.jpg'
            )
        else:
            return '', 404
    except Exception as e:
        print(f"Error getting menu image: {e}")
        return '', 404

#Used to add new items to the restaurant  
@app.route('/Add_item/<int:restaurant_id>', methods=['GET','POST'])
@admin_required  # Only admins can add new items to menus
def Add_item(restaurant_id):
    if request.method == 'POST':
        try:
            item_name = request.form['item_name']
            item_description = request.form['item_description']
            item_ingredients = request.form['item_ingredients']
            item_price = float(request.form['item_price'])
            item_catagory = request.form['item_catagory']
            cooking_time = float(request.form['cooking_time'])
            spice_level = request.form['spice_level']
            calories = float(request.form['calories'])

            # Handle checkbox values (only present in form if checked)
            vegetarian = 1 if 'vegetarian' in request.form else 0
            chef_special = 1 if 'chef_special' in request.form else 0

            #Handles image upload
            item_image_data = None
            if 'item_image' in request.files:
                file = request.files['item_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    item_image_data = file.read()

            # Add date_added field
            from datetime import datetime
            date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            conn = get_db_connection()
            conn.execute('''
                INSERT INTO menu_items (restaurant_id, name, description, ingredients, price, category, cooking_time, spice_level, calories, chef_special, vegetarian, available, date_added, image_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (restaurant_id, item_name, item_description, item_ingredients, item_price, item_catagory, cooking_time, spice_level, calories, chef_special, vegetarian, 1, date_added, item_image_data))
            conn.commit()
            conn.close()
           
            flash('Item added successfully!', 'success')
            return redirect(url_for('view_restaurant', restaurant_id=restaurant_id))

        except Exception as e:
            print(f"Error adding item: {e}")
            flash(f'Error: {str(e)}', 'error')

    context = get_user_context()
    context['restaurant_id'] = restaurant_id
    return render_template('View_Restaurant/Add_item.html', **context)

#Loads the page to add the item to cart
@app.route('/Add_to_cart/<int:item_id>')
def view_item(item_id):
    conn = get_db_connection()
    menu_item = conn.execute('''
        SELECT * FROM menu_items WHERE id = ?
    ''', (item_id,)).fetchone()
   
    # Add this check to prevent None errors
    if not menu_item:
        flash('Menu item not found!', 'error')
        conn.close()
        return redirect(url_for('homepage'))
   
    conn.close()
   
    context = get_user_context()
    context['menu_item'] = menu_item
    return render_template('view_restaurant/Add_to_cart.html', **context)

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    try:
        conn = get_db_connection()
       
        # Get the restaurant_id before deleting the item
        result = conn.execute('SELECT restaurant_id FROM menu_items WHERE id = ?', (item_id,))
        item = result.fetchone()
       
        if not item:
            flash('Item not found!', 'error')
            conn.close()
            return redirect(url_for('homepage'))
       
        restaurant_id = item['restaurant_id']
       
        # Delete the item
        conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
       
        flash('Item deleted successfully!', 'success')
       
        # Check if we're coming from the item detail page
        if request.referrer and 'Add_to_cart' in request.referrer:
            # If deleting from item detail page, go to restaurant page
            return redirect(url_for('view_restaurant', restaurant_id=restaurant_id))
        else:
            # If deleting from restaurant page, stay on restaurant page
            return redirect(request.referrer or url_for('view_restaurant', restaurant_id=restaurant_id))
   
    except Exception as e:
        print(f"Error deleting item: {e}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('homepage'))

@app.route('/edit_item/<int:item_id>/<int:restaurant_id>', methods=['GET', 'POST'])
@admin_required  # Only admins can edit restaurants
def edit_item(item_id, restaurant_id):
    conn = get_db_connection()
   
    if request.method == 'POST':
        try:          
            item_name = request.form['item_name']
            item_description = request.form['item_description']
            item_ingredients = request.form['item_ingredients']
            item_price = float(request.form['item_price'])
            item_catagory = request.form['item_catagory']
            cooking_time = float(request.form['cooking_time'])
            spice_level = request.form['spice_level']
            calories = float(request.form['calories'])

            # Handle checkbox values (only present in form if checked)
            vegetarian = 1 if 'vegetarian' in request.form else 0
            chef_special = 1 if 'chef_special' in request.form else 0

            # Handle image upload
            item_image_data = None
            update_image = False
           
            if 'item_image' in request.files:
                file = request.files['item_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    item_image_data = file.read()
                    update_image = True
           
            # Update menu item data
            if update_image:
                conn.execute('''
                    UPDATE menu_items
                    SET name=?, description=?, ingredients=?, price=?, category=?,
                        cooking_time=?, spice_level=?, calories=?, vegetarian=?,
                        chef_special=?, image_data=?
                    WHERE id=?
                ''', (item_name, item_description, item_ingredients, item_price,
                     item_catagory, cooking_time, spice_level, calories,
                     vegetarian, chef_special, item_image_data, item_id))
            else:
                conn.execute('''
                    UPDATE menu_items
                    SET name=?, description=?, ingredients=?, price=?, category=?,
                        cooking_time=?, spice_level=?, calories=?, vegetarian=?,
                        chef_special=?
                    WHERE id=?
                ''', (item_name, item_description, item_ingredients, item_price,
                     item_catagory, cooking_time, spice_level, calories,
                     vegetarian, chef_special, item_id))
           
            conn.commit()
            conn.close()
           
            flash('Item updated successfully!', 'success')
            return redirect(url_for('view_restaurant', restaurant_id=restaurant_id))
           
        except Exception as e:
            print(f"Error updating item: {e}")
            flash(f'Error: {str(e)}', 'error')
   
    # GET request - show the form with current data
    menu_item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
   
    if not menu_item:
        flash('Menu item not found!', 'error')
        return redirect(url_for('view_restaurant', restaurant_id=restaurant_id))
   
    context = get_user_context()
    context.update({'menu_item': menu_item, 'restaurant_id': restaurant_id})
    return render_template('view_restaurant/edit_item.html', **context)

if __name__ == '__main__':
    print("Starting Flask app...")
    init_database()
    print("Database initialized")
    app.run(debug=True, host='127.0.0.1', port=5000)