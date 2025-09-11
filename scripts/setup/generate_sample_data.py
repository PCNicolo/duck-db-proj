#!/usr/bin/env python3
"""Generate sample data for DuckDB Analytics Dashboard."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import duckdb
from pathlib import Path
import urllib.request
import os

def create_sales_data(n_records: int = 100000) -> pd.DataFrame:
    """Generate sample sales transaction data."""
    print(f"Generating {n_records:,} sales records...")
    
    date_range = pd.date_range('2023-01-01', '2024-12-31', freq='H')
    
    # Product categories and their typical price ranges
    categories = {
        'Electronics': (50, 2000),
        'Clothing': (20, 200),
        'Food': (5, 50),
        'Books': (10, 60),
        'Home & Garden': (15, 500),
        'Sports': (25, 300),
        'Toys': (10, 150),
        'Beauty': (10, 100)
    }
    
    records = []
    for i in range(n_records):
        category = random.choice(list(categories.keys()))
        price_range = categories[category]
        
        records.append({
            'transaction_id': i + 1,
            'timestamp': np.random.choice(date_range),
            'customer_id': np.random.randint(1, 10000),
            'product_id': np.random.randint(1, 500),
            'product_name': f"Product_{np.random.randint(1, 500)}",
            'quantity': np.random.randint(1, 10),
            'unit_price': round(np.random.uniform(*price_range), 2),
            'category': category,
            'payment_method': np.random.choice(['Credit Card', 'PayPal', 'Debit Card', 'Cash', 'Gift Card']),
            'store_location': np.random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia']),
            'discount_percent': np.random.choice([0, 0, 0, 5, 10, 15, 20]),
            'customer_segment': np.random.choice(['Regular', 'Premium', 'VIP'])
        })
    
    df = pd.DataFrame(records)
    df['total_amount'] = (df['unit_price'] * df['quantity'] * (1 - df['discount_percent']/100)).round(2)
    
    return df

def create_customer_data(n_customers: int = 10000) -> pd.DataFrame:
    """Generate customer dimension data."""
    print(f"Generating {n_customers:,} customer records...")
    
    states = ['NY', 'CA', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI']
    
    customers = []
    for i in range(n_customers):
        registration_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1460))
        
        customers.append({
            'customer_id': i + 1,
            'first_name': f"First_{i}",
            'last_name': f"Last_{i}",
            'email': f"customer_{i}@email.com",
            'phone': f"555-{random.randint(1000, 9999)}",
            'registration_date': registration_date,
            'state': random.choice(states),
            'age_group': random.choice(['18-25', '26-35', '36-45', '46-55', '56-65', '65+']),
            'loyalty_status': random.choice(['Bronze', 'Silver', 'Gold', 'Platinum']),
            'lifetime_value': round(random.uniform(100, 10000), 2)
        })
    
    return pd.DataFrame(customers)

def create_product_data(n_products: int = 500) -> pd.DataFrame:
    """Generate product dimension data."""
    print(f"Generating {n_products:,} product records...")
    
    categories = ['Electronics', 'Clothing', 'Food', 'Books', 'Home & Garden', 'Sports', 'Toys', 'Beauty']
    
    products = []
    for i in range(n_products):
        category = random.choice(categories)
        
        products.append({
            'product_id': i + 1,
            'product_name': f"Product_{i}",
            'category': category,
            'subcategory': f"{category}_Sub_{random.randint(1, 5)}",
            'brand': f"Brand_{random.randint(1, 50)}",
            'supplier': f"Supplier_{random.randint(1, 20)}",
            'unit_cost': round(random.uniform(5, 500), 2),
            'unit_price': round(random.uniform(10, 1000), 2),
            'stock_quantity': random.randint(0, 1000),
            'reorder_point': random.randint(10, 100),
            'discontinued': random.choice([False, False, False, False, True])
        })
    
    df = pd.DataFrame(products)
    df['profit_margin'] = ((df['unit_price'] - df['unit_cost']) / df['unit_price'] * 100).round(2)
    
    return df

def create_web_logs(n_logs: int = 50000) -> pd.DataFrame:
    """Generate web server log data."""
    print(f"Generating {n_logs:,} web log entries...")
    
    endpoints = [
        '/api/users', '/api/products', '/api/orders', '/api/cart',
        '/home', '/products', '/checkout', '/login', '/register',
        '/search', '/category', '/account', '/help', '/about'
    ]
    
    user_agents = [
        'Mozilla/5.0 Chrome/120.0.0.0',
        'Mozilla/5.0 Firefox/121.0',
        'Mozilla/5.0 Safari/17.2',
        'Mozilla/5.0 Edge/120.0.0.0'
    ]
    
    logs = []
    for _ in range(n_logs):
        timestamp = datetime.now() - timedelta(hours=random.randint(0, 720))
        
        logs.append({
            'ip_address': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            'timestamp': timestamp,
            'method': random.choice(['GET', 'GET', 'GET', 'POST', 'PUT', 'DELETE']),
            'endpoint': random.choice(endpoints),
            'status_code': random.choices([200, 201, 204, 301, 404, 500], weights=[70, 5, 5, 5, 10, 5])[0],
            'response_time_ms': random.randint(50, 2000),
            'user_agent': random.choice(user_agents),
            'referrer': random.choice(['google.com', 'facebook.com', 'direct', 'twitter.com', 'linkedin.com']),
            'session_id': f"session_{random.randint(1, 10000)}"
        })
    
    return pd.DataFrame(logs)

def create_inventory_data(products_df: pd.DataFrame) -> pd.DataFrame:
    """Generate inventory movement data."""
    print("Generating inventory movement records...")
    
    movements = []
    for _ in range(10000):
        product = products_df.sample(1).iloc[0]
        
        movements.append({
            'movement_id': len(movements) + 1,
            'product_id': product['product_id'],
            'movement_date': datetime.now() - timedelta(days=random.randint(0, 365)),
            'movement_type': random.choice(['Purchase', 'Sale', 'Return', 'Adjustment']),
            'quantity': random.randint(-100, 100),
            'warehouse': random.choice(['Warehouse_A', 'Warehouse_B', 'Warehouse_C']),
            'unit_cost': product['unit_cost'],
            'notes': random.choice(['Regular movement', 'Seasonal stock', 'Clearance', 'New arrival'])
        })
    
    return pd.DataFrame(movements)

def download_external_data():
    """Download external datasets."""
    print("\nDownloading external datasets...")
    
    data_dir = Path("data/samples")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Try to download a small sample dataset
    try:
        url = 'https://raw.githubusercontent.com/datablist/sample-csv-files/main/files/customers/customers-100.csv'
        filepath = data_dir / "external_customers.csv"
        
        if not filepath.exists():
            print("Downloading customer sample data...")
            urllib.request.urlretrieve(url, filepath)
            print(f"Downloaded: {filepath}")
    except Exception as e:
        print(f"Could not download external data: {e}")

def setup_duckdb_database():
    """Set up DuckDB database with sample data and TPC-H."""
    print("\nSetting up DuckDB database...")
    
    conn = duckdb.connect('analytics.db')
    
    # Install and load TPC-H extension
    try:
        print("Installing TPC-H extension...")
        conn.execute("INSTALL tpch")
        conn.execute("LOAD tpch")
        conn.execute("CALL dbgen(sf=0.01)")  # Small scale factor for demo
        print("TPC-H data generated successfully!")
        
        # Show available TPC-H tables
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"TPC-H tables available: {[t[0] for t in tables]}")
    except Exception as e:
        print(f"Could not set up TPC-H: {e}")
    
    # Create views for CSV/Parquet files
    data_dir = Path("data/samples")
    
    for csv_file in data_dir.glob("*.csv"):
        table_name = csv_file.stem
        conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{csv_file}')")
        print(f"Created view: {table_name}")
    
    for parquet_file in data_dir.glob("*.parquet"):
        table_name = parquet_file.stem
        conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{parquet_file}')")
        print(f"Created view: {table_name}")
    
    # Run sample queries
    print("\n" + "="*50)
    print("Sample Analytics Queries")
    print("="*50)
    
    # Query 1: Top categories by revenue
    try:
        result = conn.execute("""
            SELECT 
                category,
                COUNT(*) as transactions,
                SUM(total_amount) as total_revenue,
                AVG(total_amount) as avg_transaction
            FROM sales_data
            GROUP BY category
            ORDER BY total_revenue DESC
            LIMIT 5
        """).fetchdf()
        print("\nTop 5 Categories by Revenue:")
        print(result)
    except Exception as e:
        print(f"Query failed: {e}")
    
    # Query 2: Daily sales trend
    try:
        result = conn.execute("""
            SELECT 
                DATE(timestamp) as sale_date,
                COUNT(*) as num_transactions,
                SUM(total_amount) as daily_revenue
            FROM sales_data
            GROUP BY sale_date
            ORDER BY sale_date DESC
            LIMIT 10
        """).fetchdf()
        print("\nRecent Daily Sales:")
        print(result)
    except Exception as e:
        print(f"Query failed: {e}")
    
    conn.close()
    print("\nDatabase setup complete!")

def main():
    """Main function to generate all sample data."""
    print("="*60)
    print("DuckDB Analytics Dashboard - Sample Data Generator")
    print("="*60)
    
    # Create data directory
    data_dir = Path("data/samples")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate datasets
    print("\nGenerating sample datasets...")
    
    # Sales data
    sales_df = create_sales_data(100000)
    sales_df.to_csv(data_dir / "sales_data.csv", index=False)
    sales_df.to_parquet(data_dir / "sales_data.parquet", index=False)
    print(f"✓ Saved sales_data.csv and sales_data.parquet ({len(sales_df):,} rows)")
    
    # Customer data
    customers_df = create_customer_data(10000)
    customers_df.to_csv(data_dir / "customers.csv", index=False)
    customers_df.to_parquet(data_dir / "customers.parquet", index=False)
    print(f"✓ Saved customers.csv and customers.parquet ({len(customers_df):,} rows)")
    
    # Product data
    products_df = create_product_data(500)
    products_df.to_csv(data_dir / "products.csv", index=False)
    products_df.to_parquet(data_dir / "products.parquet", index=False)
    print(f"✓ Saved products.csv and products.parquet ({len(products_df):,} rows)")
    
    # Web logs
    logs_df = create_web_logs(50000)
    logs_df.to_csv(data_dir / "web_logs.csv", index=False)
    logs_df.to_parquet(data_dir / "web_logs.parquet", index=False)
    print(f"✓ Saved web_logs.csv and web_logs.parquet ({len(logs_df):,} rows)")
    
    # Inventory data
    inventory_df = create_inventory_data(products_df)
    inventory_df.to_csv(data_dir / "inventory.csv", index=False)
    inventory_df.to_parquet(data_dir / "inventory.parquet", index=False)
    print(f"✓ Saved inventory.csv and inventory.parquet ({len(inventory_df):,} rows)")
    
    # Download external data
    download_external_data()
    
    # Set up DuckDB database
    setup_duckdb_database()
    
    print("\n" + "="*60)
    print("✨ Sample data generation complete!")
    print("="*60)
    print("\nYou can now:")
    print("1. Run the Streamlit app: streamlit run app.py")
    print("2. Use the CLI tool: python -m duckdb_analytics.cli")
    print("3. Query the analytics.db database directly")
    print("\nSample files are in: data/samples/")

if __name__ == "__main__":
    main()