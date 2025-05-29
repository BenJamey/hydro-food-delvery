import sqlite3
import os
from datetime import datetime

def init_db():
    """Initialize the database with all required tables and sample data"""
    
    # Check if database exists
    db_exists = os.path.exists('HFD_Data.db')
   
    # Connect to database
    conn = sqlite3.connect('HFD_Data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
   
    # Restaurant table
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
    
    # Menu items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER,
        name TEXT NOT NULL,
        description TEXT,
        ingredients TEXT,
        price FLOAT NOT NULL,
        category TEXT NOT NULL,
        cooking_time INTEGER,
        spice_level TEXT,
        calories INTEGER,
        chef_special BOOLEAN DEFAULT 0,
        vegetarian BOOLEAN DEFAULT 0,
        available BOOLEAN DEFAULT 1,
        date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
        image_data BLOB,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
    )
    ''')

    #User account table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users_list (
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        isAdmin BOOLEAN DEFAULT 0
    )''')
 
    # Only insert sample data if database didn't exist before or is empty
    restaurant_count = cursor.execute('SELECT COUNT(*) FROM restaurants').fetchone()[0]
    
    if restaurant_count == 0:
        print("Adding sample restaurants...")
        # Insert sample restaurants
        restaurants = [
            ('Subway', 4.3, 2.5, 'fast_food', 'Subway primarily sells sandwiches and healthy fast food options'),
            ('Tank', 4.6, 2.0, 'fast_food', 'Tank primarily sells drinks and energy beverages'),
            ('One Sushi', 4.5, 2.5, 'sushi_bar', 'One Sushi primarily sells fresh sushi and Japanese cuisine'),
            ('Noodle Kim', 4.3, 3.5, 'fast_food', 'Noodle Kim mainly sells noodle dishes and Asian cuisine')
        ]
        
        for restaurant in restaurants:
            cursor.execute('''
                INSERT INTO restaurants (rest_name, rest_score, delivery_fee, details, description) 
                VALUES (?, ?, ?, ?, ?)
            ''', restaurant)
        
        print("Adding sample menu items...")
        # Insert sample menu items
        menu_items = [
            # Subway items
            (1, 'Italian BMT', 'Delicious sandwich with pepperoni, salami, and ham', 'Pepperoni, Salami, Ham, Lettuce, Tomato, Cheese, Italian Bread', 8.99, 'Sandwiches', 5, 'Mild', 450, 0, 0, 1),
            (1, 'Veggie Delite', 'Fresh vegetarian sandwich with crisp vegetables', 'Lettuce, Tomato, Cucumber, Bell Peppers, Red Onions, Italian Bread', 6.49, 'Sandwiches', 3, 'Mild', 230, 0, 1, 1),
            (1, 'Chicken Teriyaki', 'Grilled chicken with teriyaki sauce', 'Grilled Chicken, Teriyaki Sauce, Lettuce, Tomato, Cheese', 9.49, 'Sandwiches', 7, 'Mild', 380, 0, 0, 1),
            
            # Tank items
            (2, 'Energy Boost', 'High caffeine energy drink for maximum energy', 'Caffeine, Taurine, B-Vitamins, Natural Flavors', 3.99, 'Beverages', 1, 'Mild', 160, 0, 0, 1),
            (2, 'Protein Shake', 'High protein drink for post-workout recovery', 'Whey Protein, Milk, Natural Flavors, Vitamins', 5.49, 'Beverages', 2, 'Mild', 280, 1, 0, 1),
            (2, 'Fresh Juice', 'Freshly squeezed orange juice', 'Fresh Oranges, Natural Vitamins', 4.49, 'Beverages', 2, 'Mild', 120, 0, 1, 1),
            
            # One Sushi items
            (3, 'Salmon Roll', 'Fresh salmon sushi roll with cucumber', 'Fresh Salmon, Sushi Rice, Nori, Cucumber, Wasabi', 12.99, 'Sushi', 15, 'Medium', 320, 1, 0, 1),
            (3, 'California Roll', 'Classic California roll with crab and avocado', 'Crab Meat, Avocado, Cucumber, Sushi Rice, Nori', 10.99, 'Sushi', 12, 'Mild', 290, 0, 0, 1),
            (3, 'Vegetable Roll', 'Fresh vegetable sushi roll', 'Cucumber, Avocado, Carrot, Sushi Rice, Nori', 8.99, 'Sushi', 10, 'Mild', 220, 0, 1, 1),
            (3, 'Miso Soup', 'Traditional Japanese miso soup', 'Miso Paste, Tofu, Seaweed, Green Onions', 4.99, 'Soups', 5, 'Mild', 80, 0, 1, 1),
            
            # Noodle Kim items
            (4, 'Spicy Ramen', 'Traditional spicy noodle soup with rich broth', 'Ramen Noodles, Spicy Broth, Soft Boiled Egg, Green Onions, Corn', 11.49, 'Noodles', 12, 'Hot', 580, 1, 0, 1),
            (4, 'Pad Thai', 'Classic Thai noodle dish with sweet and sour flavors', 'Rice Noodles, Tofu, Bean Sprouts, Peanuts, Tamarind Sauce', 10.99, 'Noodles', 10, 'Medium', 520, 0, 1, 1),
            (4, 'Korean Bibimbap', 'Mixed rice bowl with vegetables and sauce', 'Rice, Mixed Vegetables, Sesame Oil, Gochujang Sauce', 12.99, 'Rice Bowls', 15, 'Medium', 480, 1, 1, 1)
        ]
        
        for item in menu_items:
            cursor.execute('''
                INSERT INTO menu_items (restaurant_id, name, description, ingredients, price, category,
                                      cooking_time, spice_level, calories, chef_special, vegetarian, available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', item)
        
        print(f"Added {len(restaurants)} restaurants and {len(menu_items)} menu items.")
    else:
        print(f"Database already contains {restaurant_count} restaurants. Skipping sample data insertion.")
 
    #Adding users to database
    print("Adding user accounts to database.....")
    user_data = [
        ('User1', 'P@$$word123', 'User1@gmail.co.nz', 0)
        ('AdminUser', 'ADM_P@SS', 'AdminUSE@gmail.co.nz', 1)
    ]
    
    for user in user_data:
        cursor.execute('''
            INSERT INTO users_list (username, password, email, isAdmin)
            VALUES (?, ?, ?, ?)''', user)

    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()