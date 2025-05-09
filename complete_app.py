import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from uuid import uuid4

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE = 'ocs.db'

# Set session lifetime to 30 minutes
app.permanent_session_lifetime = timedelta(minutes=30)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def update_product(product_id, name, description, price, stock, category, image_filename=None):
    db = get_db()
    if image_filename:
        db.execute('''
            UPDATE Product
            SET name = ?, description = ?, price = ?, stock = ?, category = ?, image_filename = ?
            WHERE product_id = ?
        ''', (name, description, price, stock, category, image_filename, product_id))
    else:
        db.execute('''
            UPDATE Product
            SET name = ?, description = ?, price = ?, stock = ?, category = ?
            WHERE product_id = ?
        ''', (name, description, price, stock, category, product_id))
    db.commit()

@app.route('/')
def home():
    return redirect(url_for('products'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session.permanent = True
            session['username'] = username
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        db = get_db()
        user = db.execute('SELECT * FROM Customer WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['username'] = username
            session['user_id'] = user['customer_id']
            session['is_admin'] = False
            return redirect(url_for('products'))
        flash('Invalid credentials.')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Basic Info
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        # Personal Info Fields
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form['phone']
        status = request.form['status']
        credit = float(request.form['credit'])

        # Address Info
        address_name = request.form['address_name']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']

        # 💳 Card Info
        card_number = request.form['card_number']
        expiry = request.form['expiry']
        cvv = request.form['cvv']

        db = get_db()

        # Check for existing username
        existing_username = db.execute('SELECT * FROM Customer WHERE username = ?', (username,)).fetchone()
        if existing_username:
            flash("Username already exists. Please choose a different username.")
            return render_template('register.html', form_data=request.form)

        # Check for existing email
        existing_email = db.execute('SELECT * FROM Customer WHERE email = ?', (email,)).fetchone()
        if existing_email:
            flash("Email already exists.")
            return render_template('register.html', form_data=request.form)

        # Check for existing phone
        existing_phone = db.execute('SELECT * FROM Customer WHERE phone = ?', (phone,)).fetchone()
        if existing_phone:
            flash("Phone number already exists.")
            return render_template('register.html', form_data=request.form)

        # Proceed with registration if no duplicates
        db.execute('''
            INSERT INTO Customer (username, email, password, first_name, last_name, phone, status, credit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, password, first_name, last_name, phone, status, credit))
        db.commit()

        customer = db.execute('SELECT * FROM Customer WHERE username = ?', (username,)).fetchone()
        customer_id = customer['customer_id']

        # Insert into Address
        db.execute('''
            INSERT INTO Address (customer_id, address_name, street, city, state, zip)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (customer_id, address_name, street, city, state, zip_code))

        # Insert into CreditCard
        db.execute('''
            INSERT INTO CreditCard (customer_id, card_number, expiry, cvv)
            VALUES (?, ?, ?, ?)
        ''', (customer_id, card_number, expiry, cvv))

        db.commit()
        flash('Registered successfully. Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/products')
def products():
    category_filter = request.args.get('category')

    conn = get_db()
    if category_filter:
        products = conn.execute("SELECT * FROM Product WHERE category = ?", (category_filter,)).fetchall()
    else:
        products = conn.execute("SELECT * FROM Product").fetchall()
    conn.close()

    return render_template('products.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM Product WHERE product_id = ?', (product_id,)).fetchone()
    if not product:
        flash("Product not found.")
        return redirect(url_for('products'))
    return render_template('product_detail.html', product=product)

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    total_orders = db.execute('SELECT COUNT(*) AS count FROM Orders').fetchone()['count']
    revenue = db.execute('''
        SELECT SUM(p.price * o.quantity) AS total
        FROM Orders o
        JOIN Product p ON o.product_id = p.product_id
        WHERE o.status != 'Cancelled'
    ''').fetchone()['total'] or 0

    top_customers = db.execute('''
        SELECT c.username, COUNT(*) as order_count
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        GROUP BY c.username
        ORDER BY order_count DESC
        LIMIT 5
    ''').fetchall()

    top_products = db.execute('''
        SELECT p.name, SUM(o.quantity) as total_qty
        FROM Orders o
        JOIN Product p ON o.product_id = p.product_id
        GROUP BY p.name
        ORDER BY total_qty DESC
        LIMIT 5
    ''').fetchall()

    return render_template('admin.html',
                           total_orders=total_orders,
                           revenue=revenue,
                           top_customers=top_customers,
                           top_products=top_products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        stock = request.form['stock']
        description = request.form['description']
        category = request.form['category']  # New
        file = request.files['image']
        image_filename = None

        if file and allowed_file(file.filename):
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        db = get_db()
        db.execute('''
            INSERT INTO Product (name, price, stock, description, image_filename, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, price, stock, description, image_filename, category))
        db.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')

@app.route('/admin/customers')
def admin_customers():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    customers = db.execute('''
        SELECT customer_id, username, email, first_name, last_name, status, credit
        FROM Customer
        ORDER BY customer_id
    ''').fetchall()

    return render_template('admin_customers.html', customers=customers)

@app.route('/admin/products')
def admin_all_products():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()

    # Group products by category
    grouped_products = {}
    for product in products:
        category = product['category'] or 'Uncategorized'
        if category not in grouped_products:
            grouped_products[category] = []
        grouped_products[category].append(product)

    return render_template('admin_products.html', grouped_products=grouped_products)

@app.route('/admin/delete_customer/<int:customer_id>')
def delete_customer(customer_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    db.execute('DELETE FROM Customer WHERE customer_id = ?', (customer_id,))
    db.commit()
    flash('Customer deleted.')
    return redirect(url_for('admin_customers'))

@app.route('/admin/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    customer = db.execute('SELECT * FROM Customer WHERE customer_id = ?', (customer_id,)).fetchone()

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        status = request.form['status']
        credit = float(request.form['credit'])

        db.execute('''
            UPDATE Customer SET first_name=?, last_name=?, email=?, status=?, credit=?
            WHERE customer_id=?
        ''', (first_name, last_name, email, status, credit, customer_id))
        db.commit()
        flash('Customer updated.')
        return redirect(url_for('admin_customers'))

    return render_template('edit_customer.html', customer=customer)

def get_product_by_id(product_id):
    db = get_db()
    return db.execute('SELECT * FROM Product WHERE product_id = ?', (product_id,)).fetchone()

@app.route('/admin/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = get_product_by_id(product_id)

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        stock = request.form['stock']
        category = request.form['category']

        file = request.files.get('image')
        image_filename = None

        if file and allowed_file(file.filename):
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        # 🔁 Update product with image filename if provided
        update_product(product_id, name, description, price, stock, category, image_filename)

        flash('Product updated successfully!')
        return redirect(url_for('admin_products_by_category'))

    return render_template('edit_product.html', product=product)

@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM Product WHERE product_id = ?', (product_id,))
    db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if session.get('is_admin'):
        flash("Admins cannot access checkout.")
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    customer_id = session['user_id']

    # 🟢 Fetch saved addresses and cards
    addresses = db.execute('SELECT * FROM Address WHERE customer_id = ?', (customer_id,)).fetchall()
    cards = db.execute('SELECT * FROM CreditCard WHERE customer_id = ?', (customer_id,)).fetchall()

    # 🛒 Get cart items
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    discount = 0
    promo_code = None

    for pid, qty in cart.items():
        product = db.execute('SELECT * FROM Product WHERE product_id = ?', (pid,)).fetchone()
        if product:
            subtotal = float(product['price']) * qty
            total += subtotal
            cart_items.append({
                'id': pid,
                'name': product['name'],
                'price': product['price'],
                'quantity': qty,
                'subtotal': subtotal
            })

    if request.method == 'POST':
        promo_code = request.form.get('promo_code', '').strip()
        selected_address_id = request.form.get('address_id')
        selected_card_id = request.form.get('card_id')
        order_time = datetime.now().isoformat()
        status = 'Processing'
        transaction_id = str(int(datetime.now().timestamp()))

        # Check promo code and calculate discount
        if promo_code:
            promo = db.execute('SELECT discount_percent FROM promo_codes WHERE code = ?', (promo_code,)).fetchone()
            if promo:
                discount = float(promo['discount_percent']) / 100.0
                total = total * (1 - discount)
            else:
                flash("⚠️ Invalid promo code.")
                discount = 0.0

        for item in cart_items:
            category_row = db.execute('SELECT category FROM Product WHERE product_id = ?', (item['id'],)).fetchone()
            category = category_row['category'] if category_row else None

            db.execute('''
                INSERT INTO Orders (
                    customer_id, product_id, quantity, promo_code,
                    order_time, status, address_id, card_id, transaction_id, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id,
                item['id'],
                item['quantity'],
                promo_code,
                order_time,
                status,
                selected_address_id,
                selected_card_id,
                transaction_id,
                category
            ))

            db.execute('UPDATE Product SET stock = stock - ? WHERE product_id = ?', (item['quantity'], item['id']))

        db.commit()
        session['cart'] = {}
        flash("Order placed successfully!")

        # 👇 Pass discount and promo code in the URL for the confirmation page
        return redirect(url_for('order_confirmation',
                                transaction_id=transaction_id,
                                discount=discount,
                                promo_code=promo_code))

    return render_template('checkout.html',
                           addresses=addresses,
                           cards=cards,
                           cart_items=cart_items,
                           total=total,
                           discount=discount,
                           promo_code=promo_code)

@app.route('/order_confirmation/<transaction_id>')
def order_confirmation(transaction_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    db = get_db()
    customer_id = session['user_id']

    orders = db.execute('''
        SELECT o.*, p.name AS product_name, p.price
        FROM Orders o
        JOIN Product p ON o.product_id = p.product_id
        WHERE o.transaction_id = ?
    ''', (transaction_id,)).fetchall()

    address = None
    card = None

    if orders:
        address = db.execute('SELECT * FROM Address WHERE address_id = ?', (orders[0]['address_id'],)).fetchone()
        card = db.execute('SELECT * FROM CreditCard WHERE card_id = ?', (orders[0]['card_id'],)).fetchone()
    else:
        flash("No recent order found.")
        return redirect(url_for('products'))

    total = sum(order['quantity'] * order['price'] for order in orders)
    discount = float(request.args.get('discount', 0))
    promo_code = request.args.get('promo_code', '')

    return render_template('order_confirmation.html',
                           transaction_id=transaction_id,
                           orders=orders,
                           total=total * (1 - discount),
                           address=address,
                           card=card,
                           discount=discount,
                           promo_code=promo_code)

@app.route('/orders')
def orders():
    if session.get('is_admin'):
        flash("Admins do not have orders.")
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    orders_raw = db.execute('''
        SELECT o.*, p.name AS product_name, p.category
        FROM Orders o
        JOIN Product p ON o.product_id = p.product_id
        WHERE o.customer_id = ?
    ''', (session['user_id'],)).fetchall()

    order_list = []
    for o in orders_raw:
        order_time = datetime.fromisoformat(o['order_time']) if o['order_time'] else datetime.now()
        can_cancel = datetime.now() - order_time < timedelta(hours=24)
        order_list.append({
            'order_id': o['order_id'],
            'product_name': o['product_name'],
            'category': o['category'],
            'quantity': o['quantity'],
            'status': o['status'],
            'order_time': o['order_time'],
            'can_cancel': can_cancel
        })

    return render_template('orders.html', orders=order_list)

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    db = get_db()
    customer_id = session['user_id']

    user = db.execute('SELECT * FROM Customer WHERE customer_id = ?', (customer_id,)).fetchone()
    addresses = db.execute('SELECT * FROM Address WHERE customer_id = ?', (customer_id,)).fetchall()
    cards = db.execute('SELECT * FROM CreditCard WHERE customer_id = ?', (customer_id,)).fetchall()

    orders = db.execute('''
        SELECT o.*, p.name AS product_name
        FROM Orders o
        JOIN Product p ON o.product_id = p.product_id
        WHERE o.customer_id = ?
    ''', (customer_id,)).fetchall()

    return render_template('dashboard.html', user=user, addresses=addresses, cards=cards, orders=orders)

@app.route('/cancel_order/<int:order_id>')
def cancel_order(order_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    db = get_db()
    order = db.execute('SELECT * FROM Orders WHERE order_id = ? AND customer_id = ?', (order_id, session['user_id'])).fetchone()
    if order:
        order_time = datetime.fromisoformat(order['order_time'])
        if datetime.now() - order_time < timedelta(hours=24):
            db.execute('UPDATE Orders SET status = ? WHERE order_id = ?', ('Cancelled', order_id))
            db.commit()
            flash("Order cancelled successfully.")
    return redirect(url_for('orders'))

@app.route('/admin/orders')
def admin_orders():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')

    query = '''
        SELECT o.order_id, o.transaction_id, c.username, p.name AS product_name,
               p.category, o.quantity, o.status, o.order_time
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        JOIN Product p ON o.product_id = p.product_id
        WHERE 1=1
    '''
    params = []

    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)

    if category_filter:
        query += ' AND p.category = ?'
        params.append(category_filter)

    query += ' ORDER BY o.order_time DESC'

    orders = db.execute(query, tuple(params)).fetchall()

    return render_template('view_orders.html', orders=orders, status_filter=status_filter, category_filter=category_filter)

@app.route('/admin/products_by_category')
def admin_products_by_category():
    db = get_db()
    products = db.execute('SELECT * FROM Product ORDER BY category').fetchall()
    categorized = {}
    for product in products:
        cat = product['category'] or 'Uncategorized'
        categorized.setdefault(cat, []).append(product)
    return render_template('products_by_category.html', categorized_products=categorized)

@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
def update_order(order_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    status = request.form['status']
    db = get_db()
    db.execute('UPDATE Orders SET status = ? WHERE order_id = ?', (status, order_id))
    db.commit()
    flash("Order status updated.")
    return redirect(url_for('admin_orders'))

@app.route('/admin/create_promo', methods=['GET', 'POST'])
def create_promo():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        code = request.form['code']
        discount = request.form['discount']
        db = get_db()
        db.execute('INSERT INTO promo_codes (code, discount_percent, created_at) VALUES (?, ?, ?)',
                   (code, discount, datetime.now().isoformat()))
        db.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('create_promo.html')

@app.route('/admin/analytics')
def analytics():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    db = get_db()

    revenue = db.execute('SELECT SUM(p.price * o.quantity) AS total FROM Orders o JOIN Product p ON o.product_id = p.product_id WHERE o.status != "Cancelled"').fetchone()['total'] or 0

    top_products = db.execute('''
        SELECT p.name, COUNT(*) as count
        FROM Orders o
        JOIN Product p ON o.product_id = p.product_id
        GROUP BY p.name
        ORDER BY count DESC
        LIMIT 5
    ''').fetchall()

    top_customers = db.execute('''
        SELECT c.username, COUNT(*) as total
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        GROUP BY c.username
        ORDER BY total DESC
        LIMIT 5
    ''').fetchall()

    return render_template('analytics.html', revenue=revenue, top_products=top_products, top_customers=top_customers)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if session.get('is_admin'):
        flash("Admins do not have a profile.")
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    customer_id = session['user_id']

    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        status = request.form['status']
        credit = float(request.form['credit'])

        db.execute('''
            UPDATE Customer
            SET email = ?, phone = ?, status = ?, credit = ?
            WHERE customer_id = ?
        ''', (email, phone, status, credit, customer_id))
        db.commit()
        flash("Profile updated.")

    user = db.execute('SELECT * FROM Customer WHERE customer_id = ?', (customer_id,)).fetchone()
    return render_template('profile.html', user=user)

@app.route('/cards', methods=['GET', 'POST'])
def manage_cards():
    if session.get('is_admin'):
        flash("Admins cannot manage cards.")
        return redirect(url_for('admin_dashboard'))
    db = get_db()
    if request.method == 'POST':
        number = request.form['card_number']
        expiry = request.form['expiry']
        cvv = request.form['cvv']
        db.execute('INSERT INTO CreditCard (customer_id, card_number, expiry, cvv) VALUES (?, ?, ?, ?)',
                   (session['user_id'], number, expiry, cvv))
        db.commit()
    cards = db.execute('SELECT * FROM CreditCard WHERE customer_id = ?', (session['user_id'],)).fetchall()
    return render_template('manage_cards.html', cards=cards)

@app.route('/cards/edit/<int:card_id>', methods=['GET'])
def edit_card(card_id):
    if session.get('is_admin'):
        flash("Admins cannot manage cards.")
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    card = db.execute('''
        SELECT * FROM CreditCard 
        WHERE card_id = ? AND customer_id = ?
    ''', (card_id, session['user_id'])).fetchone()
    if not card:
        flash("Card not found.")
        return redirect(url_for('manage_cards'))

    return render_template('edit_card.html', card=card)

@app.route('/cards/edit/<int:card_id>', methods=['POST'])
def update_card(card_id):
    if session.get('is_admin'):
        flash("Admins cannot manage cards.")
        return redirect(url_for('admin_dashboard'))

    card_number = request.form['card_number']
    expiry = request.form['expiry']
    cvv = request.form['cvv']

    db = get_db()
    card = db.execute('''
        SELECT * FROM CreditCard 
        WHERE card_id = ? AND customer_id = ?
    ''', (card_id, session['user_id'])).fetchone()
    if not card:
        flash("Card not found.")
        return redirect(url_for('manage_cards'))

    db.execute('''
        UPDATE CreditCard 
        SET card_number = ?, expiry = ?, cvv = ?
        WHERE card_id = ? AND customer_id = ?
    ''', (card_number, expiry, cvv, card_id, session['user_id']))
    db.commit()
    flash("Card updated successfully.")
    return redirect(url_for('manage_cards'))

@app.route('/cards/delete/<int:card_id>', methods=['GET'])
def delete_card(card_id):
    if session.get('is_admin'):
        flash("Admins cannot manage cards.")
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    card = db.execute('''
        SELECT * FROM CreditCard 
        WHERE card_id = ? AND customer_id = ?
    ''', (card_id, session['user_id'])).fetchone()
    if not card:
        flash("Card not found.")
        return redirect(url_for('manage_cards'))

    db.execute('''
        DELETE FROM CreditCard 
        WHERE card_id = ? AND customer_id = ?
    ''', (card_id, session['user_id']))
    db.commit()
    flash("Card deleted successfully.")
    return redirect(url_for('manage_cards'))

@app.route('/addresses', methods=['GET', 'POST'])
def manage_addresses():
    if session.get('is_admin'):
        flash("Admins cannot manage addresses.")
        return redirect(url_for('admin_dashboard'))
    db = get_db()
    if request.method == 'POST':
        name = request.form['address_name']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        db.execute('INSERT INTO Address (customer_id, address_name, street, city, state, zip) VALUES (?, ?, ?, ?, ?, ?)',
                   (session['user_id'], name, street, city, state, zip_code))
        db.commit()
    addresses = db.execute('SELECT * FROM Address WHERE customer_id = ?', (session['user_id'],)).fetchall()
    return render_template('manage_addresses.html', addresses=addresses)

@app.route('/addresses/edit/<int:address_id>', methods=['GET'])
def edit_address(address_id):
    if session.get('is_admin'):
        flash("Admins cannot manage addresses.")
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    address = db.execute('''
        SELECT * FROM Address
        WHERE address_id = ? AND customer_id = ?
    ''', (address_id, session['user_id'])).fetchone()

    if not address:
        flash("Address not found.")
        return redirect(url_for('manage_addresses'))

    return render_template('edit_address.html', address=address)

@app.route('/addresses/edit/<int:address_id>', methods=['POST'])
def update_address(address_id):
    if session.get('is_admin'):
        flash("Admins cannot manage addresses.")
        return redirect(url_for('admin_dashboard'))

    address_name = request.form['address_name']
    street = request.form['street']
    city = request.form['city']
    state = request.form['state']
    zip_code = request.form['zip']

    db = get_db()
    db.execute('''
        UPDATE Address
        SET address_name = ?, street = ?, city = ?, state = ?, zip = ?
        WHERE address_id = ? AND customer_id = ?
    ''', (address_name, street, city, state, zip_code, address_id, session['user_id']))
    db.commit()

    flash("Address updated successfully.")
    return redirect(url_for('manage_addresses'))

@app.route('/addresses/delete/<int:address_id>', methods=['GET'])
def delete_address(address_id):
    if session.get('is_admin'):
        flash("Admins cannot manage addresses.")
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    db.execute('''
        DELETE FROM Address
        WHERE address_id = ? AND customer_id = ?
    ''', (address_id, session['user_id']))
    db.commit()

    flash("Address deleted successfully.")
    return redirect(url_for('manage_addresses'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if not session.get('user_id'):
        flash("Please login or register to add products to cart.")
        return redirect(url_for('login'))

    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    session['cart'] = cart
    flash("Product added to cart.")
    return redirect(url_for('products'))

@app.route('/cart')
def cart():
    if session.get('is_admin'):
        flash("Admins do not have a cart.")
        return redirect(url_for('admin_dashboard'))

    cart = session.get('cart', {})
    db = get_db()
    cart_items = []
    total = 0
    for pid, qty in cart.items():
        product = db.execute('SELECT * FROM Product WHERE product_id = ?', (pid,)).fetchone()
        if product:
            subtotal = float(product['price']) * qty
            total += subtotal
            cart_items.append({
                'id': pid,
                'name': product['name'],
                'price': product['price'],
                'quantity': qty,
                'subtotal': subtotal
            })
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<product_id>')
def remove_from_cart(product_id):
    if 'cart' in session and product_id in session['cart']:
        session['cart'].pop(product_id)
        flash('Item removed from cart.')
    return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True, port=5003)