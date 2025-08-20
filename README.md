# 🦆 DuckDB Analytics Dashboard

A powerful local data analytics dashboard built on DuckDB for analyzing CSV and Parquet files with zero-copy SQL queries.

## Features

- **Zero-Copy Analytics**: Query files directly without loading into memory
- **Web Dashboard**: Interactive Streamlit interface for data exploration
- **CLI Tool**: Command-line interface for quick queries and data operations
- **Multiple Data Formats**: Support for CSV and Parquet files
- **SQL Editor**: Full SQL support with query templates and execution plans
- **Visualizations**: Built-in charts and graphs using Plotly
- **Data Management**: File upload, conversion, and catalog management
- **Sample Data**: Includes data generator for testing and demos

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd duck-db-proj
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Generate sample data:
```bash
python generate_sample_data.py
```

### Running the Dashboard

Start the Streamlit web interface:
```bash
streamlit run app.py
```

Open your browser and navigate to http://localhost:8501

### Using the CLI

The CLI provides quick access to data exploration:

```bash
# List available tables
python -m duckdb_analytics.cli tables

# Execute a query
python -m duckdb_analytics.cli query "SELECT * FROM sales_data LIMIT 10"

# Load a CSV file
python -m duckdb_analytics.cli load data.csv --table-name my_data

# Interactive mode
python -m duckdb_analytics.cli interactive

# Get help
python -m duckdb_analytics.cli --help
```

## Project Structure

```
duck-db-proj/
├── src/duckdb_analytics/     # Core package
│   ├── core/                 # DuckDB connection and query engine
│   ├── data/                 # File management and ingestion
│   └── cli.py               # Command-line interface
├── app.py                    # Streamlit dashboard
├── generate_sample_data.py   # Sample data generator
├── data/samples/            # Sample data files
└── analytics.db             # DuckDB database file
```

## Dashboard Features

### SQL Editor Tab
- Write and execute custom SQL queries
- Query templates for common operations
- Execution plan visualization
- Export results as CSV or Parquet

### Analytics Tab
- Pre-built analytics functions
- Summary statistics
- Missing value analysis
- Custom aggregations

### Visualizations Tab
- Line charts, bar charts, scatter plots
- Histograms and box plots
- Correlation heatmaps
- Interactive Plotly visualizations

### Data Explorer Tab
- Interactive data filtering
- Column-wise exploration
- Export filtered datasets

## CLI Commands

| Command | Description |
|---------|-------------|
| `query` | Execute SQL query |
| `load` | Load CSV/Parquet file |
| `tables` | List available tables |
| `describe` | Show table schema |
| `preview` | Preview table data |
| `stats` | Show table statistics |
| `scan` | Scan directory for data files |
| `convert` | Convert CSV to Parquet |
| `explain` | Show query execution plan |
| `interactive` | Start interactive mode |

## Sample Queries

```sql
-- Top products by revenue
SELECT 
    product_name,
    SUM(total_amount) as revenue,
    COUNT(*) as transactions
FROM sales_data
GROUP BY product_name
ORDER BY revenue DESC
LIMIT 10;

-- Customer segmentation analysis
SELECT 
    c.customer_segment,
    COUNT(DISTINCT s.customer_id) as customers,
    SUM(s.total_amount) as total_revenue
FROM sales_data s
JOIN customers c ON s.customer_id = c.customer_id
GROUP BY c.customer_segment;

-- Time series analysis
SELECT 
    DATE_TRUNC('day', timestamp) as date,
    COUNT(*) as daily_transactions,
    SUM(total_amount) as daily_revenue
FROM sales_data
GROUP BY date
ORDER BY date;
```

## Performance Tips

1. **Use Parquet Format**: Convert CSV files to Parquet for better performance
2. **Leverage DuckDB's Columnar Engine**: Write queries that scan only needed columns
3. **Create Views**: Use views for frequently accessed filtered datasets
4. **Query Caching**: The dashboard automatically caches query results
5. **Parallel Processing**: DuckDB automatically parallelizes query execution

## Data Sources

The project includes a data generator that creates:
- Sales transactions (100K records)
- Customer data (10K records)
- Product catalog (500 products)
- Web server logs (50K entries)
- Inventory movements (10K records)

You can also load your own CSV/Parquet files through the dashboard or CLI.

## Requirements

- Python 3.10+
- DuckDB 0.9.0+
- Streamlit 1.28.0+
- Pandas 2.0.0+
- See `requirements.txt` for full list

## License

MIT License - See LICENSE file for details