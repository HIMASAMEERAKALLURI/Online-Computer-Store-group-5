-- Turn off foreign key checks temporarily
PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- Create a new Orders table with full schema, including address and card references
CREATE TABLE Orders_new (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    promo_code TEXT,
    order_time TEXT,
    status TEXT,
    address_id INTEGER,       -- ✅ new column
    card_id INTEGER,          -- ✅ new column
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id),
    FOREIGN KEY (address_id) REFERENCES Address(address_id),
    FOREIGN KEY (card_id) REFERENCES CreditCard(card_id)
);

-- Migrate old data into the new table (nulls for new address_id/card_id)
INSERT INTO Orders_new (
    order_id, customer_id, product_id, quantity, promo_code, order_time, status
)
SELECT order_id, customer_id, product_id, quantity, promo_code, order_time, status
FROM Orders;

-- Replace the old Orders table
DROP TABLE Orders;
ALTER TABLE Orders_new RENAME TO Orders;

COMMIT;

-- Re-enable foreign key checks
PRAGMA foreign_keys = ON;