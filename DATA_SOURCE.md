Great! Here are some excellent data sources you can use immediately:

## **Quick-Start Data Sources (No Login Required)**

### 1. **Built-in DuckDB Sample Data**
```python
import duckdb

# TPC-H benchmark data (built into DuckDB!)
conn = duckdb.connect()
conn.execute("INSTALL tpch; LOAD tpch")
conn.execute("CALL dbgen(sf=0.1)")  # Generates sample sales data
conn.execute("SELECT * FROM lineitem LIMIT 10").fetchdf()
```

### 2. **Direct Download URLs (No Account Needed)**

```python
import duckdb
import urllib.request

# NYC Taxi Data (Parquet format - perfect for DuckDB)
duckdb.sql("""
    SELECT * FROM read_parquet('https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet')
    LIMIT 1000
""").show()

# GitHub Archive Data
duckdb.sql("""
    SELECT * FROM read_json_auto('https://data.gharchive.org/2024-01-01-0.json.gz')
    LIMIT 100
""")

# Sample CSVs from GitHub
urllib.request.urlretrieve(
    'https://raw.githubusercontent.com/datablist/sample-csv-files/main/files/customers/customers-100000.csv',
    'customers.csv'
)
```

### 3. **Sample Datasets with Direct Links**

```bash
# E-commerce Data
wget https://github.com/datablist/sample-csv-files/raw/main/files/orders/orders.csv
wget https://github.com/datablist/sample-csv-files/raw/main/files/customers/customers-100.csv
wget https://github.com/datablist/sample-csv-files/raw/main/files/products/products.csv

# Web Server Logs (Apache/Nginx format)
wget https://raw.githubusercontent.com/elastic/examples/master/Common%20Data%20Formats/apache_logs/apache_logs
```

### 4. **Python Script to Generate Sample Data**

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Generate sample sales data
def create_sample_data():
    # Sales transactions
    n_records = 100000
    date_range = pd.date_range('2023-01-01', '2024-12-31', freq='H')
    
    sales_data = pd.DataFrame({
        'transaction_id': range(1, n_records + 1),
        'timestamp': np.random.choice(date_range, n_records),
        'customer_id': np.random.randint(1, 10000, n_records),
        'product_id': np.random.randint(1, 500, n_records),
        'quantity': np.random.randint(1, 10, n_records),
        'price': np.random.uniform(10, 500, n_records).round(2),
        'category': np.random.choice(['Electronics', 'Clothing', 'Food', 'Books'], n_records),
        'payment_method': np.random.choice(['Credit Card', 'PayPal', 'Cash'], n_records),
        'store_location': np.random.choice(['NYC', 'LA', 'Chicago', 'Houston'], n_records)
    })
    
    # Save as CSV and Parquet
    sales_data.to_csv('sales_data.csv', index=False)
    sales_data.to_parquet('sales_data.parquet', index=False)
    
    # Generate web logs
    log_entries = []
    for _ in range(50000):
        log_entries.append({
            'ip': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            'timestamp': datetime.now() - timedelta(hours=random.randint(0, 720)),
            'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
            'endpoint': random.choice(['/api/users', '/api/products', '/home', '/login', '/checkout']),
            'status_code': random.choice([200, 200, 200, 404, 500, 301]),
            'response_time_ms': random.randint(50, 2000)
        })
    
    pd.DataFrame(log_entries).to_csv('web_logs.csv', index=False)

create_sample_data()
```

### 5. **Kaggle Datasets (Great Options)**

If you want to use Kaggle, here are perfect datasets for DuckDB:

- **[Walmart Sales](https://www.kaggle.com/datasets/yasserh/walmart-dataset)** - Multiple CSVs to join
- **[E-Commerce Data](https://www.kaggle.com/datasets/carrie1/ecommerce-data)** - Real transaction data
- **[Web Server Logs](https://www.kaggle.com/datasets/eliasdabbas/web-server-access-logs)** - Real Apache logs
- **[Netflix Shows](https://www.kaggle.com/datasets/shivamb/netflix-shows)** - Good for aggregations

### 6. **Quick Setup Script**

```python
#!/usr/bin/env python3
import duckdb
import pandas as pd

# Create a sample project structure
def setup_project():
    conn = duckdb.connect('analytics.db')
    
    # Load NYC Taxi data directly
    print("Loading NYC Taxi data...")
    conn.execute("""
        CREATE OR REPLACE TABLE taxi_trips AS 
        SELECT * FROM read_parquet('https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet')
        LIMIT 100000
    """)
    
    # Create sample queries
    print("\nSample analysis:")
    
    # Average fare by hour
    result = conn.execute("""
        SELECT 
            HOUR(tpep_pickup_datetime) as hour,
            AVG(fare_amount) as avg_fare,
            COUNT(*) as num_trips
        FROM taxi_trips
        GROUP BY hour
        ORDER BY hour
    """).fetchdf()
    
    print(result.head(10))
    
    return conn

if __name__ == "__main__":
    conn = setup_project()
```

**Pro tip**: Start with the NYC Taxi parquet files or the TPC-H built-in data - they're perfect for learning DuckDB's strengths with large datasets and don't require any downloads or accounts!