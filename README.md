# 🦆 DuckDB Analytics Dashboard

A powerful local data analytics platform built on DuckDB for analyzing CSV and Parquet files with natural language queries, zero-copy SQL execution, and interactive visualizations.

## ✨ Features

### Core Capabilities
- **Zero-Copy Analytics**: Query files directly without loading into memory
- **Natural Language Queries**: Convert plain English to SQL using local LLM integration
- **Interactive Dashboard**: Modern Streamlit interface with multiple analysis modes
- **Smart Visualizations**: Automatic chart recommendations based on data patterns
- **Performance Optimized**: M1 Pro optimized with 66% latency reduction in SQL generation

### Data & Query Features
- **Multiple Formats**: Native support for CSV and Parquet files
- **SQL Editor**: Advanced editor with syntax highlighting and auto-completion
- **Query Explanation**: Automatic explanations for generated SQL queries
- **Schema Intelligence**: Cached schema extraction for faster query generation
- **Connection Pooling**: Efficient connection management for concurrent operations

### Visualization & Export
- **Chart Types**: Line, bar, scatter, histogram, box plots, heatmaps
- **Export Options**: CSV, Parquet, and direct chart downloads
- **Real-time Updates**: Live query results and visualizations
- **Sample Data**: Built-in data generator for testing and demos

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Local LLM server running at `http://localhost:1234/v1` (optional, for natural language queries)
- 4GB+ RAM recommended
- macOS (M1/M2 optimized) or Linux/Windows

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

1. Start the Streamlit web interface:
```bash
streamlit run app.py
```

2. Open your browser and navigate to http://localhost:8501

3. (Optional) For natural language queries, ensure your local LLM server is running at `http://localhost:1234/v1`

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

## 📁 Project Structure

```
duck-db-proj/
├── src/duckdb_analytics/     # Core package
│   ├── core/                 # DuckDB connection and query engine
│   │   ├── connection.py     # Optimized M1 connection management
│   │   ├── connection_pool.py # Connection pooling
│   │   └── query_engine.py   # Query execution and caching
│   ├── llm/                  # LLM integration
│   │   ├── enhanced_sql_generator.py  # Natural language to SQL
│   │   ├── schema_extractor.py        # Schema caching
│   │   └── query_explainer.py         # SQL explanations
│   ├── ui/                   # UI components
│   │   ├── sql_editor.py     # Advanced SQL editor
│   │   ├── chat_interface.py # Natural language interface
│   │   ├── enhanced_thinking_pad.py # Query generation process
│   │   └── visualizer.py     # Chart generation
│   ├── visualizations/       # Visualization engine
│   │   └── recommendation_engine.py  # Smart chart suggestions
│   ├── data/                 # File management and ingestion
│   └── cli.py               # Command-line interface
├── app.py                    # Streamlit dashboard
├── generate_sample_data.py   # Sample data generator
├── test_sql_generation.py    # SQL generation tests
├── CLAUDE.md                # AI assistant guidance
├── data/samples/            # Sample data files
└── analytics.db             # DuckDB database file
```

## 🎯 Dashboard Features

### Natural Language Interface
- **Chat Interface**: Ask questions in plain English
- **SQL Generation**: Automatic conversion to optimized SQL
- **Query Explanation**: Understand what the generated SQL does
- **Thinking Process**: Visual feedback during query generation

### SQL Editor Tab
- **Advanced Editor**: Syntax highlighting and auto-completion
- **Query Templates**: Pre-built templates for common operations
- **Execution Plans**: Visual query plan analysis
- **Export Options**: Save results as CSV or Parquet
- **Query History**: Access previously executed queries

### Analytics Tab
- **Summary Statistics**: Comprehensive data profiling
- **Missing Value Analysis**: Identify and handle nulls
- **Distribution Analysis**: Histograms and percentiles
- **Custom Aggregations**: Group-by operations with multiple metrics
- **Time Series Analysis**: Trend detection and seasonality

### Visualizations Tab
- **Smart Recommendations**: AI-suggested chart types based on data
- **Interactive Charts**: Plotly-powered visualizations
- **Chart Types**: Line, bar, scatter, histogram, box plots, heatmaps
- **Customization**: Titles, labels, colors, and themes
- **Export**: Download charts as images or HTML

### Data Management Tab
- **File Upload**: Drag-and-drop CSV/Parquet files
- **Table Registry**: View and manage loaded tables
- **Schema Explorer**: Inspect table structures and data types
- **Data Preview**: Quick table previews with sampling
- **Format Conversion**: Convert between CSV and Parquet

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