# HA CyberCircuit – Online Computer Store (DMSD Final Project)

This is a full-featured Flask + SQLite web application developed as a final project for the Database Management Systems Design (DMSD) course. It allows customers to browse and purchase products, and admins to manage orders, stock, and revenue analytics.

## Features

### Customer Side
- Register and login
- Browse products by category
- Add to cart and checkout
- Save addresses and credit cards
- View order history and receipts
- Cancel items within 24 hours
- Apply promo codes

### ️ Admin Side
- Add/edit/delete products
- View and update orders
- View customers and stats
- Create promo codes
- Export tables to CSV
- View analytics dashboard

##️ Run the Project

1. Clone the repo:
   git clone https://github.com/HIMASAMEERAKALLURI/Online-Computer-Store-group-5.git

2. Create virtual environment (optional):
   python3 -m venv venv
   source venv/bin/activate

3. Install requirements:
   pip install flask

4. Run the app:
   python complete_app.py
   Visit http://127.0.0.1:5003

## Contributors
- Hima Sameera Kalluri
- Rukhsar Agheem

## Notes
- Stock updates, refunds, and analytics handled automatically
- All DB updates auto-exported to CSV
- Receipt shows total, promo, and refund details
