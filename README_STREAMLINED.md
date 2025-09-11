# 📊 SQL Analytics Studio - Streamlined Version

A radically simplified SQL analytics tool focused on two core features:
1. **Natural Language to SQL** - Chat interface powered by LM Studio
2. **Smart Visualization** - Auto-detecting chart types with manual override

## ✨ What's New

This streamlined version removes complexity and focuses on essentials:
- ✅ **Single-page interface** - Everything visible at once
- ✅ **Side-by-side layout** - Chat helper next to SQL editor
- ✅ **Smart charts** - Auto-detects best visualization
- ✅ **Minimal UI** - Maximum space for content
- ❌ **Removed** - CLI, analytics tabs, complex filters, dashboard builder

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start LM Studio
- Download and run [LM Studio](https://lmstudio.ai/)
- Load any SQL-capable model
- Ensure it's running on `http://localhost:1234`

### 3. Run the App
```bash
streamlit run app.py
```

### 4. Load Data
- Click "Load Sample Data" for test data
- Or upload your own CSV/Parquet files

### 5. Query Your Data
- **Option A**: Type natural language in the chat ("Show total sales by month")
- **Option B**: Write SQL directly in the editor
- Click "Run Query" to execute

## 🎯 Features

### Chat Helper
- Converts natural language to SQL
- Powered by your local LM Studio model
- One-click transfer to SQL editor
- Works offline with your data

### SQL Editor
- Clean, simple interface
- Manual editing of generated queries
- Syntax highlighting
- Direct query execution

### Smart Visualization
- **Auto mode**: Detects best chart type
- **Manual override**: Choose from line, bar, scatter, pie, heatmap
- **Table view**: See raw data
- Export capabilities (coming soon)

## 📁 Project Structure

```
app.py                    # Main streamlined application
src/
├── duckdb_analytics/
│   ├── core/            # Database connection (kept)
│   ├── llm/             # LM Studio integration (kept)
│   ├── ui/              # Simplified UI components
│   │   ├── chat_interface.py
│   │   ├── sql_editor.py
│   │   └── visualizer.py
│   └── visualizations/  # Smart chart detection
│       ├── chart_types.py
│       └── recommendation_engine.py
```

## 🔄 Migration from Old Version

### What's Removed
- Command-line interface (CLI)
- Analytics templates and profiler
- Multiple visualization tabs
- Data explorer tab
- Complex filtering and pagination
- Dashboard builder
- Query execution plans

### What's Kept
- Core DuckDB functionality
- LM Studio integration
- CSV/Parquet file upload
- Sample data generation
- Basic query execution

## 🛠️ Troubleshooting

### LM Studio Not Connected
- Ensure LM Studio is running on port 1234
- Check that a model is loaded
- Restart the app after starting LM Studio

### Import Errors
- Run `pip install -r requirements.txt`
- Ensure Python 3.10+ is installed

### No Data Showing
- Click "Load Sample Data" first
- Or upload a CSV/Parquet file
- Check that your query returns results

## 📊 Example Queries

### Natural Language
- "Show total sales by month"
- "Which products have the highest revenue?"
- "List top 10 customers by order count"

### Direct SQL
```sql
SELECT 
    DATE_TRUNC('month', order_date) as month,
    SUM(amount) as total_sales
FROM sales
GROUP BY month
ORDER BY month;
```

## 🚦 Status

- ✅ Core functionality working
- ✅ Natural language to SQL
- ✅ Smart visualization
- ✅ File upload
- 🚧 Export functionality (coming soon)
- 🚧 Query history (planned)

## 📝 License

Same as original project

---

**Note**: This is a streamlined version focusing on simplicity and core functionality. For the full-featured version with CLI, analytics tabs, and advanced features, see the main branch.