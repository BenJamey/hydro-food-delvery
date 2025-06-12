from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask import Flask, render_template, redirect, url_for, flash, request
import sqlite3
import os
import io
 
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
 
# Test route to check if Flask is working
@app.route('/test')
def test():
    return "<h1>Flask is working!</h1><p>If you see this, the Flask app is running correctly.</p>"
 
@app.route('/')
def homepage():
    try:
        conn = get_db_connection()
        restaurants = conn.execute('SELECT * FROM restaurants ORDER BY rest_score DESC').fetchall()
        conn.close()
        print(f"Found {len(restaurants)} restaurants")  # Debug print
        return render_template('index.html', restaurants=restaurants)
    except Exception as e:
        print(f"Error in homepage: {e}")  # Debug print
        return f"<h1>Error:</h1><p>{str(e)}</p><p><a href='/test'>Test Flask</a></p>"
 
@app.route('/add_restaurant', methods=['GET', 'POST'])
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
   
    return render_template('add_restaurant.html')
 
@app.route('/edit_restaurant/<int:restaurant_id>', methods=['GET', 'POST'])
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
   
    return render_template('edit_restaurant.html', restaurant=restaurant)
 
@app.route('/delete_restaurant/<int:restaurant_id>', methods=['POST'])
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
def upload_bulk_images():
    """Route to upload multiple images at once"""
    return render_template('bulk_upload.html')
 
@app.route('/upload_bulk_images', methods=['POST'])
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
 
    memu_items = conn.execute('SELECT * FROM menu_items WHERE restaurant_id = ? ORDER BY price', (restaurant_id,)).fetchall()
    print(f"Found {len(memu_items)} items")  # Debug print
    conn.close()
 
    return render_template('view_restaurant/view.html', restaurant=restaurant, memu_items=memu_items)

#Loads the menu where the user can upload an imagre for the food
@app.route('/add_menu_image/<int:menu_id>', methods=['GET', 'POST'])
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
 
    return render_template('view_restaurant/Add_image.html', menu_item=menu_item)
 
# ADD THIS NEW ROUTE to serve menu item images
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

 #Used to add new items to the retauraunt   
#Used to add new items to the restaurant  
@app.route('/Add_item/<int:restaurant_id>', methods=['GET','POST'])
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
            calories = float(request.form['calories'])  # Fixed: was request.file['calories']

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
 
    return render_template('View_Restaurant/Add_item.html', restaurant_id=restaurant_id)

#restaurant_id
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
   
    memu_items = conn.execute('SELECT * FROM menu_items ORDER BY price').fetchall()
    print(f"Found {len(memu_items)} items")  # Debug print
    conn.close()
   
    return render_template('view_restaurant/Add_to_cart.html', menu_item=menu_item)


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
   
    return render_template('view_restaurant/edit_item.html', menu_item=menu_item, restaurant_id=restaurant_id)

if __name__ == '__main__':
    print("Starting Flask app...")
    init_database()
    print("Database initialized")
    app.run(debug=True, host='127.0.0.1', port=5000)