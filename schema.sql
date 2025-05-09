-- Customers Table
CREATE TABLE IF NOT EXISTS Customer (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    password TEXT NOT NULL
);

-- Products Table
CREATE TABLE IF NOT EXISTS Product (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    description TEXT,
    image_filename TEXT
);

-- Orders Table
CREATE TABLE IF NOT EXISTS Orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    promo_code TEXT,
    order_time TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

-- Promo Codes Table
CREATE TABLE IF NOT EXISTS promo_codes (
    code TEXT PRIMARY KEY,
    discount_percent REAL NOT NULL,
    created_at TEXT NOT NULL
);

-- Credit Cards Table
CREATE TABLE IF NOT EXISTS CreditCard (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    card_number TEXT NOT NULL,
    expiry TEXT NOT NULL,
    cvv TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
);

-- Addresses Table
CREATE TABLE IF NOT EXISTS Address (
    address_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    address_name TEXT NOT NULL,
    street TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
);

-- Add UNIQUE constraints to existing Customer table
ALTER TABLE Customer ADD CONSTRAINT unique_email UNIQUE (email);
ALTER TABLE Customer ADD CONSTRAINT unique_phone UNIQUE (phone);
ALTER TABLE Customer ADD CONSTRAINT unique_username UNIQUE (username);