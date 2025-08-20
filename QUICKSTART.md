# 🚀 Quick Start Guide - DuckDB Analytics Dashboard

## Your Data is Ready!

You already have data files in `data/samples/`:
- `sales_data.csv/parquet` - 100K sales transactions
- `customers.csv/parquet` - 10K customer records  
- `products.csv/parquet` - 500 products
- `web_logs.csv/parquet` - 50K web server logs
- `inventory.csv/parquet` - 10K inventory movements

## Start the Dashboard

Just run:
```bash
streamlit run app.py
```

The dashboard will automatically load all your data files on startup!

## Try These Sample Queries

### 1. Top Selling Products
```sql
SELECT 
    product_name,
    SUM(total_amount) as revenue,
    COUNT(*) as sales_count
FROM sales_data
GROUP BY product_name
ORDER BY revenue DESC
LIMIT 10
```

### 2. Sales by Category and Location
```sql
SELECT 
    category,
    store_location,
    COUNT(*) as transactions,
    SUM(total_amount) as total_revenue,
    AVG(total_amount) as avg_sale
FROM sales_data
GROUP BY category, store_location
ORDER BY total_revenue DESC
```

### 3. Customer Analysis with Joins
```sql
SELECT 
    c.loyalty_status,
    COUNT(DISTINCT s.customer_id) as customers,
    SUM(s.total_amount) as total_revenue,
    AVG(s.total_amount) as avg_order_value
FROM sales_data s
JOIN customers c ON s.customer_id = c.customer_id
GROUP BY c.loyalty_status
ORDER BY total_revenue DESC
```

### 4. Time Series Analysis
```sql
SELECT 
    DATE_TRUNC('day', timestamp) as sale_date,
    COUNT(*) as daily_transactions,
    SUM(total_amount) as daily_revenue,
    AVG(total_amount) as avg_transaction
FROM sales_data
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY sale_date
ORDER BY sale_date
```

### 5. Product Performance with Inventory
```sql
SELECT 
    p.product_name,
    p.category,
    p.stock_quantity,
    COUNT(s.transaction_id) as sales_count,
    SUM(s.total_amount) as revenue
FROM products p
LEFT JOIN sales_data s ON p.product_id = s.product_id
GROUP BY p.product_name, p.category, p.stock_quantity
HAVING sales_count > 0
ORDER BY revenue DESC
LIMIT 20
```

### 6. Web Traffic Analysis
```sql
SELECT 
    endpoint,
    method,
    COUNT(*) as request_count,
    AVG(response_time_ms) as avg_response_time,
    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
FROM web_logs
GROUP BY endpoint, method
ORDER BY request_count DESC
```

### 7. Customer Segmentation
```sql
SELECT 
    age_group,
    state,
    loyalty_status,
    COUNT(*) as customer_count,
    AVG(lifetime_value) as avg_lifetime_value
FROM customers
GROUP BY age_group, state, loyalty_status
ORDER BY avg_lifetime_value DESC
```

## Dashboard Features to Try

### SQL Editor Tab
1. Copy any query above into the SQL editor
2. Click "Execute" to run
3. Results appear below with metrics
4. Export as CSV or Parquet

### Analytics Tab
1. Select a table (e.g., "sales_data")
2. Use "Summary Statistics" for quick insights
3. Build custom aggregations with the UI

### Visualizations Tab
1. Run a query first to get data
2. Choose visualization type
3. Select columns for axes
4. Interactive Plotly charts

### Data Explorer Tab
1. Select any table
2. Use filters to narrow down data
3. Export filtered results

## CLI Quick Commands

```bash
# List all tables
python -m duckdb_analytics.cli tables

# Quick query
python -m duckdb_analytics.cli query "SELECT COUNT(*) FROM sales_data"

# Interactive mode
python -m duckdb_analytics.cli interactive

# Get table statistics
python -m duckdb_analytics.cli stats sales_data

# Preview data
python -m duckdb_analytics.cli preview customers --rows 20
```

## Performance Tips

- Use Parquet files (already created) for 5-10x faster queries
- The `_parquet` suffixed tables use Parquet format
- Query results are automatically cached
- DuckDB handles queries on 100K+ rows effortlessly

## Next Steps

1. Upload your own CSV/Parquet files via the sidebar
2. Create custom visualizations in the Visualizations tab
3. Save frequently used queries as templates
4. Export analysis results for reporting

Enjoy exploring your data with DuckDB! 🦆