import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('ocs.db')

# List of tables to export
tables = ['Customer', 'Product', 'Orders', 'CreditCard', 'Address', 'promo_codes']

# Loop through each table
for table in tables:
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    df.to_csv(f'{table}.csv', index=False)  # 🔄 Save as CSV
    print(f"✅ Exported {table}.csv")

conn.close()