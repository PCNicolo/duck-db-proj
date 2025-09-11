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
│   └── data/                 # File management and ingestion
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


## 💬 Natural Language Query Examples

Ask questions in plain English and get SQL + visualizations:

- "Show me top 10 products by revenue"
- "What's the average order value by customer segment?"
- "Plot daily sales trends for the last month"
- "Which products have the highest profit margins?"
- "Show customer distribution by region"
- "Compare this month's sales to last month"

## 📊 Sample SQL Queries

```sql
-- Top products by revenue with profit analysis
SELECT 
    product_name,
    SUM(total_amount) as revenue,
    SUM(total_amount * 0.3) as estimated_profit,
    COUNT(*) as transactions,
    AVG(total_amount) as avg_transaction_value
FROM sales_data
GROUP BY product_name
ORDER BY revenue DESC
LIMIT 10;

-- Customer lifetime value analysis
WITH customer_metrics AS (
    SELECT 
        customer_id,
        COUNT(*) as purchase_count,
        SUM(total_amount) as lifetime_value,
        MIN(timestamp) as first_purchase,
        MAX(timestamp) as last_purchase
    FROM sales_data
    GROUP BY customer_id
)
SELECT 
    c.customer_segment,
    COUNT(DISTINCT cm.customer_id) as customers,
    AVG(cm.lifetime_value) as avg_lifetime_value,
    AVG(cm.purchase_count) as avg_purchases
FROM customer_metrics cm
JOIN customers c ON cm.customer_id = c.customer_id
GROUP BY c.customer_segment
ORDER BY avg_lifetime_value DESC;

-- Advanced time series with moving averages
WITH daily_sales AS (
    SELECT 
        DATE_TRUNC('day', timestamp) as date,
        COUNT(*) as transactions,
        SUM(total_amount) as revenue
    FROM sales_data
    GROUP BY date
)
SELECT 
    date,
    transactions,
    revenue,
    AVG(revenue) OVER (
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as revenue_7day_avg,
    revenue - LAG(revenue) OVER (ORDER BY date) as daily_change
FROM daily_sales
ORDER BY date DESC
LIMIT 30;
```

## ⚡ Performance Optimization

### Recent Improvements (v2.0)
- **66% Latency Reduction**: SQL generation optimized from ~10s to <2s
- **Schema Caching**: Intelligent caching reduces redundant database queries
- **Connection Pooling**: Efficient connection management for concurrent operations
- **M1 Pro Optimization**: Tuned for Apple Silicon with 4 threads and 2GB memory limit

### Best Practices
1. **Use Parquet Format**: 5-10x faster than CSV for analytical queries
2. **Leverage Zero-Copy**: Query files directly without loading into memory
3. **Column Selection**: Only query columns you need to minimize I/O
4. **Create Views**: Use views for frequently accessed filtered datasets
5. **Query Caching**: Dashboard automatically caches results for 5 minutes
6. **Batch Operations**: Use batch inserts for large data loads

## 📊 Data Sources

### Sample Data Generator
The project includes a comprehensive data generator that creates realistic datasets:
- **Sales Transactions**: 100K records with products, customers, amounts
- **Customer Data**: 10K customers with segments and demographics
- **Product Catalog**: 500 products across multiple categories
- **Web Server Logs**: 50K entries for log analysis
- **Inventory Movements**: 10K records for supply chain analysis

### Loading Your Own Data
- **Dashboard Upload**: Drag-and-drop interface for CSV/Parquet files
- **File Browser**: Navigate and select local data files
- **Directory Scan**: Auto-discover data files in a directory
- **URL Loading**: Direct loading from HTTP/S3 URLs (coming soon)

## 📋 Requirements

### Core Dependencies
- **Python**: 3.10+ (3.11 recommended)
- **DuckDB**: 0.9.0+ (columnar database engine)
- **Streamlit**: 1.28.0+ (web dashboard)
- **Pandas**: 2.0.0+ (data manipulation)
- **Plotly**: 5.17.0+ (interactive visualizations)

### LLM Integration (Optional)
- **OpenAI Client**: For natural language queries
- **Local LLM Server**: Compatible with OpenAI API format
- **Recommended**: LM Studio, Ollama, or similar

### Full dependency list in `requirements.txt`

## 🚧 Roadmap

### Coming Soon
- [ ] Cloud storage integration (S3, GCS, Azure)
- [ ] Advanced ML-powered insights
- [ ] Collaborative features and sharing
- [ ] Custom dashboard templates
- [ ] API endpoints for programmatic access
- [ ] Docker containerization
- [ ] Real-time data streaming support

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with [DuckDB](https://duckdb.org/) - The fast in-process analytical database
- UI powered by [Streamlit](https://streamlit.io/) - The fastest way to build data apps
- Visualizations by [Plotly](https://plotly.com/) - Interactive graphing library