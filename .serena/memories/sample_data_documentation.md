# Sample Data Files for SQL Analytics Studio

## Data Overview
This directory contains 5 sample CSV files with e-commerce and web analytics data for testing the SQL Analytics Studio. All files are auto-loaded on application startup.

## File Details

### 📊 customers.csv
- **Size**: 930 KB (10,000 rows × 10 columns)
- **Description**: Customer demographics and loyalty information
- **Columns**: 
  - `customer_id` (int): Unique customer identifier
  - `first_name` (str): Customer first name
  - `last_name` (str): Customer last name  
  - `email` (str): Customer email address
  - `phone` (str): Phone number
  - `registration_date` (date): Account creation date
  - `state` (str): US state code
  - `age_group` (str): Age bracket (e.g., "36-45")
  - `loyalty_status` (str): Tier level (Silver/Gold/Platinum)
  - `lifetime_value` (float): Total purchase value

### 📦 inventory.csv
- **Size**: 792 KB (10,000 rows × 8 columns)
- **Description**: Warehouse inventory movements and stock levels
- **Columns**:
  - `movement_id` (int): Unique movement identifier
  - `product_id` (int): Product reference
  - `movement_date` (date): Transaction date
  - `movement_type` (str): IN/OUT/ADJUSTMENT
  - `quantity` (int): Units moved
  - `warehouse` (str): Location identifier
  - `unit_cost` (float): Cost per unit
  - `notes` (str): Additional information

### 🛍️ products.csv
- **Size**: 45 KB (500 rows × 12 columns)
- **Description**: Product catalog with pricing and inventory details
- **Columns**:
  - `product_id` (int): Unique product identifier
  - `product_name` (str): Product display name
  - `category` (str): Main category
  - `subcategory` (str): Sub-category
  - `brand` (str): Brand name
  - `supplier` (str): Supplier company
  - `unit_cost` (float): Cost price
  - `unit_price` (float): Selling price
  - `stock_quantity` (int): Current stock
  - `reorder_point` (int): Minimum stock threshold
  - `discontinued` (bool): Availability status
  - `profit_margin` (float): Profit percentage

### 💰 sales_data.csv
- **Size**: 9.75 MB (100,000 rows × 13 columns)
- **Description**: Transaction history with customer and product details
- **Columns**:
  - `transaction_id` (int): Unique transaction identifier
  - `timestamp` (datetime): Sale timestamp
  - `customer_id` (int): Customer reference (→ customers.csv)
  - `product_id` (int): Product reference (→ products.csv)
  - `product_name` (str): Product name at sale time
  - `quantity` (int): Units purchased
  - `unit_price` (float): Price per unit
  - `category` (str): Product category
  - `payment_method` (str): Payment type
  - `store_location` (str): Store identifier
  - `discount_percent` (float): Applied discount
  - `customer_segment` (str): Customer classification
  - `total_amount` (float): Final transaction amount

### 🌐 web_logs.csv
- **Size**: 5.71 MB (50,000 rows × 9 columns)
- **Description**: Website access logs and performance metrics
- **Columns**:
  - `ip_address` (str): Client IP address
  - `timestamp` (datetime): Request timestamp
  - `method` (str): HTTP method (GET/POST/PUT/DELETE)
  - `endpoint` (str): API endpoint accessed
  - `status_code` (int): HTTP response code
  - `response_time_ms` (int): Server response time
  - `user_agent` (str): Browser/client identifier
  - `referrer` (str): Referral source
  - `session_id` (str): User session identifier

## Relationships
- `customers.customer_id` ← `sales_data.customer_id` (1:many)
- `products.product_id` ← `sales_data.product_id` (1:many)
- `products.product_id` ← `inventory.product_id` (1:many)

## Sample Queries
```sql
-- Top selling products
SELECT product_name, SUM(quantity) as units_sold
FROM sales_data 
GROUP BY product_name 
ORDER BY units_sold DESC LIMIT 10;

-- Customer lifetime value analysis
SELECT c.loyalty_status, AVG(c.lifetime_value) as avg_ltv
FROM customers c
GROUP BY c.loyalty_status;

-- Inventory turnover
SELECT p.product_name, p.stock_quantity, COUNT(s.transaction_id) as sales_count
FROM products p
LEFT JOIN sales_data s ON p.product_id = s.product_id
GROUP BY p.product_name, p.stock_quantity
ORDER BY sales_count DESC;
```

## Notes
- All files are UTF-8 encoded CSV format
- Dates are in YYYY-MM-DD format
- Timestamps include time: YYYY-MM-DD HH:MM:SS
- Monetary values are in USD
- Data is synthetic and for demonstration purposes only